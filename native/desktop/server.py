"""Mac-owned local service, reusing the accounting reference runtime and verifier.

HTTPS, one-time bootstrap/phone association, real configured vision and durable local state.
This is a single-company local runtime, not the unfinished multi-tenant Vultr deployment.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import ssl
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit, urlencode, quote

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(HERE), str(REPO / "frontend/dev-mock-api")]
_spec = importlib.util.spec_from_file_location("ledgerflow_reference_server", REPO / "frontend/dev-mock-api/server.py")
api = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = api
_spec.loader.exec_module(api)  # reference rules, sandbox and independent verifier
import assistant
from store import Store


def local_addresses():
    result = {"127.0.0.1"}
    output = subprocess.run(["/sbin/ifconfig"], capture_output=True, text=True, check=True).stdout
    for value in re.findall(r"\binet (\d+\.\d+\.\d+\.\d+)", output):
        address = ipaddress.ip_address(value)
        if address.is_private and not address.is_link_local:
            result.add(value)
    # Prefer the actual Wi-Fi interface over private VPN/VM interfaces in the QR.
    preferred=[]
    ports=subprocess.run(["/usr/sbin/networksetup","-listallhardwareports"],capture_output=True,text=True).stdout
    match=re.search(r"Hardware Port: (?:Wi-Fi|AirPort)\nDevice: ([A-Za-z0-9]+)",ports)
    if match:
        block=re.search(r"^"+re.escape(match[1])+r":.*?(?=^\S|\Z)",output,re.M|re.S)
        if block:
            preferred=[v for v in re.findall(r"\binet (\d+\.\d+\.\d+\.\d+)",block[0]) if v in result]
    return ["127.0.0.1",*preferred,*sorted(result-{"127.0.0.1",*preferred})]


def certificate(directory, addresses):
    key, cert = directory / "tls-key.pem", directory / "tls-cert.pem"
    manifest = directory / "tls-hosts.json"
    valid=cert.exists() and subprocess.run(["/usr/bin/openssl","x509","-checkend","86400","-noout","-in",str(cert)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if not key.exists() or not valid or not manifest.exists() or json.loads(manifest.read_text()) != addresses:
        conf = directory / "tls.cnf"
        sans = ",".join(["DNS:localhost"] + [f"IP:{value}" for value in addresses])
        conf.write_text("[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n[dn]\nCN=LedgerFlow Local\n[ext]\nsubjectAltName=" + sans + "\nbasicConstraints=critical,CA:TRUE\nkeyUsage=critical,digitalSignature,keyEncipherment,keyCertSign\nextendedKeyUsage=serverAuth\n")
        subprocess.run(["/usr/bin/openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048", "-days", "365", "-config", str(conf), "-keyout", str(key), "-out", str(cert)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.chmod(key, 0o600)
        manifest.write_text(json.dumps(addresses))
    der = ssl.PEM_cert_to_DER_cert(cert.read_text())
    return cert, key, hashlib.sha256(der).hexdigest()


def install_routes(store, bootstrap, addresses, fingerprint, port, allow_samples=False):
    pairings = {}
    consumed_bootstrap = False
    chat_busy = set()
    api.DB.setdefault("assistant_messages", [])
    original_emit = api.emit
    dirty = threading.Event()

    def flush():
        with api.LOCK:
            store.save(api.DB)

    def emit(*args, **kwargs):
        result = original_emit(*args, **kwargs)
        dirty.set()
        return result
    api.emit = emit

    def writer():
        while True:
            dirty.wait()
            time.sleep(.2)
            dirty.clear()
            try: flush()
            except Exception:
                # The next HTTP mutation also performs a synchronous save and reports a failure.
                sys.stderr.write("Local workspace background save failed.\n")
    threading.Thread(target=writer, daemon=True).start()

    def session(role, uid, name):
        sid, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        value = {"user_id":uid,"role":role,"display_name":name,"tenant_id":"ten_nordvik", "csrf_token":csrf,
                 "expires_at":(datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%SZ")}
        api.DB["sessions"][sid] = value
        return 201, {**value,"backend":"LOCAL","inference":"vultr" if api.vsi.enabled() else "unavailable"}, {"Set-Cookie": f"ledgerflow_session={sid}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=28800"}

    @api.route("POST", "/desktop/bootstrap", auth=False)
    def start(ctx):
        nonlocal consumed_bootstrap
        request = api.jbody(ctx)
        with api.LOCK:
            if consumed_bootstrap or not secrets.compare_digest(str(request.get("token", "")), bootstrap) or ctx["handler"].client_address[0] != "127.0.0.1":
                raise api.ApiError(401,"BOOTSTRAP_INVALID","Relancez l’application Mac pour ouvrir votre espace.")
            consumed_bootstrap = True
            return session("owner", "usr_local_owner", "Mon espace")

    @api.route("GET", "/desktop/status")
    def status(ctx):
        return 200, {"mode":"local", "model":api.vsi.MODEL if api.vsi.enabled() else None, "vision":api.vsi.enabled(),
                     "docker":api.sandbox.docker_available(), "image_ready":api.sandbox.image_available(),
                     "phone_available":len(addresses)>1, "persistent":True, "assistant":True}

    @api.route("GET", "/desktop/workspace-profile", roles=("owner",))
    def workspace_profile(ctx):
        with api.LOCK:
            return 200, {"profile": api.DB.get("desktop_workspace_profile")}

    @api.route("POST", "/desktop/workspace-profile", roles=("owner",))
    def save_workspace_profile(ctx):
        if ctx["handler"].client_address[0] != "127.0.0.1":
            raise api.ApiError(403, "MAC_REQUIRED", "Change the workspace profile on its Mac.")
        body = api.jbody(ctx)
        name, source = body.get("name"), body.get("source")
        sources = ("excel", "fortnox", "visma", "quickbooks", "sap", "dynamics", "other")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or source not in sources:
            raise api.ApiError(400, "INVALID_WORKSPACE_PROFILE", "Enter a workspace name and select an accounting source.")
        with api.LOCK:
            profile = {"name": name.strip(), "source": source}
            api.DB["desktop_workspace_profile"] = profile
        return 200, {"profile": profile}

    @api.route("POST", "/desktop/pairings", roles=("owner",), idem=True)
    def pair(ctx):
        body = api.jbody(ctx)
        scope = body.get("scope", "capture")
        if scope not in ("capture", "workspace"):
            raise api.ApiError(400,"INVALID_SCOPE","Choisissez capture ou espace complet.")
        peers = [v for v in addresses if v != "127.0.0.1"]
        if not peers:
            raise api.ApiError(409,"NO_LOCAL_NETWORK","Connectez le Mac et l’iPhone au même réseau Wi-Fi.")
        with api.LOCK:
            for identifier,p in list(pairings.items()):
                if p["deadline"] < time.time(): del pairings[identifier]
            if len(pairings) >= 10: raise api.ApiError(429,"PAIRING_LIMIT","Fermez un code existant puis réessayez.")
            token, pid = secrets.token_urlsafe(32), api.oid("pair")
            pairings[pid] = {"digest":api.sha(token.encode()),"deadline":time.time()+120,"uid":ctx["session"]["user_id"],"scope":scope}
        origin = f"https://{peers[0]}:{port}"
        link = "ledgerflow://connect?"+urlencode({"origin":origin,"pin":fingerprint,"mode":scope})+"#"+token
        return 201,{"pairing_id":pid,"url":link,"expires_at":(datetime.now(timezone.utc)+timedelta(seconds=120)).isoformat(),"scope":scope}

    @api.route("DELETE", "/desktop/pairings/([A-Za-z0-9_\\-]+)",roles=("owner",))
    def unpair(ctx,pid):
        with api.LOCK:
            value=pairings.get(pid)
            if value and value["uid"] != ctx["session"]["user_id"]: raise api.ApiError(403,"FORBIDDEN","Ce code appartient à un autre utilisateur.")
            pairings.pop(pid,None)
        return 200,{"ok":True}

    @api.route("POST", "/desktop/pairings/exchange",auth=False)
    def exchange(ctx):
        token = str(api.jbody(ctx).get("token", ""))
        if not 32 <= len(token) <= 100: raise api.ApiError(401,"PAIRING_INVALID","Le code est invalide ou expiré. Générez-en un autre sur le Mac.")
        digest=api.sha(token.encode())
        with api.LOCK:
            found=next(((pid,p) for pid,p in pairings.items() if secrets.compare_digest(p["digest"],digest)),None)
            if not found or found[1]["deadline"] <= time.time(): raise api.ApiError(401,"PAIRING_INVALID","Le code est invalide ou expiré. Générez-en un autre sur le Mac.")
            pid,p=found
            del pairings[pid]  # atomic single use, never persisted
            return session("owner" if p["scope"] == "workspace" else "employee",p["uid"] if p["scope"]=="workspace" else "usr_phone_capture","Mon iPhone")

    @api.route("GET", "/assistant/messages")
    def messages(ctx):
        uid=ctx["session"]["user_id"]
        with api.LOCK: items=[m for m in api.DB["assistant_messages"] if m["user_id"]==uid][-80:]
        return 200,{"items":items}

    @api.route("POST", "/assistant/messages",idem=True)
    def chat(ctx):
        body=api.jbody(ctx)
        text=body.get("text", "")
        if not isinstance(text,str) or not 1<=len(text.strip())<=3000: raise api.ApiError(400,"MESSAGE_INVALID","Votre message doit contenir entre 1 et 3 000 caractères.")
        if not api.vsi.enabled(): raise api.ApiError(503,"INFERENCE_UNAVAILABLE","Le modèle de vision n’est pas configuré sur ce Mac. Consultez « Connexion du modèle » dans Réglages.",True)
        uid, role=ctx["session"]["user_id"],ctx["session"]["role"]
        with api.LOCK:
            if uid in chat_busy: raise api.ApiError(409,"ASSISTANT_BUSY","Une réponse est déjà en cours.",True)
            chat_busy.add(uid)
            runs=[api.snapshot(r,role) for r in api.DB["runs"].values() if role!="employee" or r.get("created_by")==uid][-25:]
            workbooks=[api.workbook_view(w) for w in api.DB["workbooks"].values()]
            history=[m for m in api.DB["assistant_messages"] if m["user_id"]==uid]
        user={"id":api.oid("msg"),"role":"user","text":text.strip(),"user_id":uid,"created_at":api.now(),"actions":[]}
        try:
            context={"role":role,"workbooks":[{"name":w["display_name"],"status":w["status"],"versions":w["version_count"]} for w in workbooks],
                     "documents":[{"merchant":r.get("transaction",{}).get("merchant_name") if r.get("transaction") else None,"state":r["state"],"review_items":r.get("review_items",[]),"amount_minor":(r.get("transaction") or {}).get("gross_minor"),"currency":(r.get("transaction") or {}).get("currency")} for r in runs],
                     "vision_model":api.vsi.MODEL,"storage":"Mac local; iPhone sur le même réseau via QR; LedgerFlow actif et Mac éveillé. Fermer la fenêtre laisse le moteur actif; quitter LedgerFlow ou mettre le Mac en veille coupe l’accès iPhone."}
            result,meta=assistant.answer(api.vsi,context,[*history,user],body.get("language") if body.get("language") in assistant.LANGUAGES else "fr")
            allowed={"capture","overview"} if role=="employee" else set(assistant.SCHEMA["properties"]["actions"]["items"]["enum"])
            reply={"id":api.oid("msg"),"role":"assistant","text":result["answer"],"actions":[a for a in result["actions"] if a in allowed],"user_id":uid,"created_at":api.now(),"model":meta["model_id"]}
            with api.LOCK: api.DB["assistant_messages"].extend([user,reply])
            return 201,{"items":[user,reply]}
        except api.vsi.VsiError as exc:
            raise api.ApiError(503,"ASSISTANT_UNAVAILABLE","Le modèle ne répond pas pour le moment. Votre message peut être réessayé.",True) from exc
        finally:
            with api.LOCK: chat_busy.discard(uid)

    original_routes=list(api.ROUTES)
    additions=original_routes[original_routes.index(next(r for r in original_routes if r[2] is start)):]
    # Disable development invites and samples in the actual desktop runtime.
    api.ROUTES[:]=additions+[r for r in original_routes if r not in additions and not (r[0]=="POST" and r[1].pattern=="^/api/v1/auth/session$") and (allow_samples or "/dev/" not in r[1].pattern)]

    class DesktopHandler(api.Handler):
        server_version="LedgerFlowLocal/1"
        def log_message(self,*args): pass  # never log bearer fragments, filenames or receipt data

        def _session(self):
            value=super()._session()
            if value and datetime.fromisoformat(value["expires_at"].replace("Z","+00:00"))>datetime.now(timezone.utc): return value
            return None

        def _json(self,status,obj,headers=None):
            if isinstance(obj,dict) and obj.get("backend")=="DEV-MOCK": obj={**obj,"backend":"LOCAL","inference":"vultr" if api.vsi.enabled() else "unavailable"}
            if self.command in ("POST","DELETE") and status<400: flush()
            super()._json(status,obj,headers)

        def send_header(self,key,value):
            if key.lower()=="x-ledgerflow-backend": value="LOCAL"
            if key.lower()=="content-disposition" and 'filename="' in value:
                name=value.split('filename="',1)[1].rsplit('"',1)[0]
                name=Path(name.replace("\\","/")).name.replace("\r","").replace("\n","")
                fallback=re.sub(r'[^A-Za-z0-9._ -]',"_",name) or "workbook.xlsx"
                value=f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(name,safe="")}'
            super().send_header(key,value)

        def end_headers(self):
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Referrer-Policy","no-referrer")
            self.send_header("Content-Security-Policy","default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
            super().end_headers()

        def _static(self,path):
            target=(api.DIST/path.lstrip("/")).resolve()
            if not target.is_relative_to(api.DIST.resolve()): return self._err(api.ApiError(404,"NOT_FOUND","Fichier introuvable."))
            return super()._static(path)

        def _dispatch(self,method):
            host=self.headers.get("Host", "")
            permitted={f"{address}:{port}" for address in addresses}|{f"localhost:{port}"}
            if host not in permitted: return self._err(api.ApiError(403,"HOST_INVALID","Adresse non autorisée."))
            request_origin=self.headers.get("Origin")
            if method!="GET" and request_origin and request_origin!="https://"+host:
                return self._err(api.ApiError(403,"ORIGIN_INVALID","Origine non autorisée."))
            if self.headers.get("Sec-Fetch-Site")=="cross-site": return self._err(api.ApiError(403,"ORIGIN_INVALID","Origine non autorisée."))
            return super()._dispatch(method)
    return DesktopHandler,flush


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--data-dir",type=Path,required=True)
    parser.add_argument("--status-file",type=Path,required=True)
    parser.add_argument("--parent-pid",type=int)
    parser.add_argument("--allow-samples",action="store_true")
    args=parser.parse_args()
    os.umask(0o077)
    store=Store(args.data_dir)
    import fcntl
    lock=(args.data_dir/"runtime.lock").open("a")
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    saved=store.load()
    if saved is not None: api.DB.update(saved)
    for run in api.DB["runs"].values():
        if run["state"] not in {"COMMITTED","CANCELLED","REJECTED","FAILED","EXPIRED","AWAITING_APPROVAL","NEEDS_REVIEW","DUPLICATE_REVIEW","STALE_BASE"}:
            api.set_state(run,"FAILED","APP_INTERRUPTED","Le Mac a été arrêté pendant le traitement. Relancez cette pièce depuis sa fiche.")
    api.vsi.load_dotenv()
    # No automatic mocked extraction in the delivered Mac application.
    if not api.vsi.enabled():
        def unavailable(*a,**k): raise api.ApiError(503,"INFERENCE_UNAVAILABLE","Le modèle de vision n’est pas configuré.")
        def start_unavailable(run_id, from_stage="EXTRACTING"):
            with api.LOCK:
                run=api.DB["runs"][run_id]
                run["transaction"]=api.blank_transaction(api.DB["documents"][run["document_id"]],run)
                api.set_state(run,"NEEDS_REVIEW","INFERENCE_UNAVAILABLE","Le modèle de vision n’est pas configuré. Rien n’a été écrit.")
        api.start_run_worker=start_unavailable
    addresses=local_addresses()
    cert,key,fingerprint=certificate(args.data_dir,addresses)
    server=api.ThreadingHTTPServer(("0.0.0.0",0),api.Handler)
    server.daemon_threads=True
    bootstrap=secrets.token_urlsafe(32)
    handler,flush=install_routes(store,bootstrap,addresses,fingerprint,server.server_port,args.allow_samples)
    server.RequestHandlerClass=handler
    tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version=ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(cert,key)
    server.socket=tls.wrap_socket(server.socket,server_side=True)
    origin=f"https://127.0.0.1:{server.server_port}"
    status={"origin":origin,"pin":fingerprint,"bootstrap":bootstrap,"pid":os.getpid()}
    args.status_file.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=args.status_file.with_suffix(".tmp")
    temporary.write_text(json.dumps(status))
    os.chmod(temporary,0o600)
    os.replace(temporary,args.status_file)
    flush()
    def stop(*_):
        flush()
        threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    if args.parent_pid:
        def parent_watch():
            while True:
                time.sleep(3)
                try: os.kill(args.parent_pid,0)
                except ProcessLookupError: stop(); return
        threading.Thread(target=parent_watch,daemon=True).start()
    try: server.serve_forever()
    finally:
        flush(); server.server_close(); args.status_file.unlink(missing_ok=True)


if __name__=="__main__": main()
