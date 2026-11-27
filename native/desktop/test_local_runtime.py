"""Security and persistence regressions for the Mac service. No real model calls."""
import copy
import importlib.util
import http.cookiejar
import json
from pathlib import Path
import secrets
import sqlite3
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parent))
_spec=importlib.util.spec_from_file_location("ledgerflow_desktop_runtime_tests",Path(__file__).with_name("server.py"))
runtime=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runtime)
from store import Store


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    directory=tmp_path_factory.mktemp("local-runtime")
    store=Store(directory)
    api=runtime.api
    bootstrap=secrets.token_urlsafe(32)
    cert,key,pin=runtime.certificate(directory,["127.0.0.1"])
    srv=api.ThreadingHTTPServer(("127.0.0.1",0),api.Handler)
    handler,flush=runtime.install_routes(store,bootstrap,["127.0.0.1","192.168.1.3"],pin,srv.server_port)
    srv.RequestHandlerClass=handler
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(cert,key)
    srv.socket=context.wrap_socket(srv.socket,server_side=True)
    threading.Thread(target=srv.serve_forever,daemon=True).start()
    base=f"https://127.0.0.1:{srv.server_port}"
    yield base,cert,bootstrap
    srv.shutdown(); srv.server_close()


class Client:
    def __init__(self,service):
        self.base,cert,_=service
        self.csrf=None
        self.op=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(cert))),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def req(self,method,path,body=None,headers=None):
        values={"Origin":self.base,"Content-Type":"application/json","Idempotency-Key":secrets.token_hex(16)}
        if self.csrf: values["X-CSRF-Token"]=self.csrf
        values.update(headers or {})
        request=urllib.request.Request(self.base+"/api/v1"+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers=values)
        try:
            with self.op.open(request,timeout=10) as response: return response.status,json.loads(response.read())
        except urllib.error.HTTPError as error: return error.code,json.loads(error.read())


@pytest.fixture(scope="module")
def owner(service):
    client=Client(service)
    code,session=client.req("POST","/desktop/bootstrap",{"token":service[2]})
    assert code==201
    client.csrf=session["csrf_token"]
    return client


def pairing(owner,scope="capture"):
    code,p=owner.req("POST","/desktop/pairings",{"scope":scope})
    assert code==201,p
    return p,urllib.parse.urlsplit(p["url"]).fragment


def test_origin_host_and_csrf_rejections(service,owner):
    assert Client(service).req("GET","/workbooks")[0]==401
    assert owner.req("GET","/workbooks",headers={"Host":"attacker.invalid"})[0]==403
    assert owner.req("POST","/desktop/pairings",{"scope":"workspace"},headers={"Origin":"https://attacker.invalid"})[0]==403
    assert owner.req("POST","/desktop/pairings",{"scope":"workspace"},headers={"X-CSRF-Token":"wrong"})[0]==403


def test_bootstrap_is_not_a_reusable_invite(service,owner):
    assert Client(service).req("POST","/desktop/bootstrap",{"token":service[2]})[0]==401
    assert Client(service).req("POST","/auth/session",{"invite_token":"owner-demo"})[0]==404


def test_capture_role_cannot_create_full_access_and_token_is_single_use(service,owner):
    _,token=pairing(owner)
    phone=Client(service)
    code,session=phone.req("POST","/desktop/pairings/exchange",{"token":token})
    assert code==201 and session["role"]=="employee"
    phone.csrf=session["csrf_token"]
    assert phone.req("POST","/desktop/pairings",{"scope":"workspace"})[0]==403
    assert Client(service).req("POST","/desktop/pairings/exchange",{"token":token})[0]==401


def test_closed_qr_is_revoked(service,owner):
    p,token=pairing(owner)
    assert owner.req("DELETE","/desktop/pairings/"+p["pairing_id"])[0]==200
    assert Client(service).req("POST","/desktop/pairings/exchange",{"token":token})[0]==401


def test_expired_qr_is_refused(service,owner,monkeypatch):
    _,token=pairing(owner)
    future=time.time()+121
    monkeypatch.setattr(runtime.time,"time",lambda:future)
    assert Client(service).req("POST","/desktop/pairings/exchange",{"token":token})[0]==401


def test_snapshot_roundtrip_preserves_binary_and_idempotency(tmp_path):
    store=Store(tmp_path)
    value={"artifacts":{"a":{"bytes":b"\x00\xff\r\nXLSX"}},"idem":{("owner","POST","/approval","request"):("hash",200,{"commit":"c"})}}
    store.save(value)
    assert Store(tmp_path).load()==value


def test_corrupted_snapshot_refuses_to_silently_reset(tmp_path):
    store=Store(tmp_path); store.save({"workbooks":{"a":"retained"}})
    with sqlite3.connect(store.path) as db: db.execute("UPDATE snapshot SET payload=?",(b"{}",))
    with pytest.raises(ValueError,match="checksum"): store.load()
