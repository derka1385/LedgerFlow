"""Bounded live check: synthetic photo -> real vision -> Docker -> verified XLSX, phone session and restart.

Uses only repository synthetic documents. Loads the existing inference configuration privately.
Never prints bootstrap tokens, cookies, model credentials or phone-association links.
"""
import hashlib
import http.cookiejar
import io
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/"frontend/dev-mock-api"))
sys.path.insert(0,str(REPO/"accounting"))
import test_mock_api as T
from ledgerflow_accounting import Workbook, baseline, detect_mapping
from PIL import Image


class Client(T.Client):
    def __init__(self,base,certificate):
        super().__init__(base)
        context=ssl.create_default_context(cafile=str(certificate))
        self.op=urllib.request.build_opener(urllib.request.HTTPSHandler(context=context),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def start(directory):
    status=directory/"ready.json"
    status.unlink(missing_ok=True)
    log=(directory/"service.log").open("ab")
    proc=subprocess.Popen([sys.executable,str(HERE/"server.py"),"--data-dir",str(directory/"data"),"--status-file",str(status)],cwd=REPO,stdout=subprocess.DEVNULL,stderr=log)
    for _ in range(150):
        if status.exists():
            details=json.loads(status.read_text())
            c=Client(details["origin"],directory/"data/tls-cert.pem")
            try:
                code,session,_=c.req("POST","/desktop/bootstrap",{"token":details["bootstrap"]})
                assert code==201,session
                c.csrf=session["csrf_token"]
                assert session["inference"]=="vultr"
                return proc,c,details
            except OSError: pass
        if proc.poll() is not None: raise AssertionError("Local runtime exited; inspect service.log")
        time.sleep(.2)
    proc.terminate()
    raise AssertionError("Local runtime did not start")


def main():
    output=REPO/"artifacts/agent-runtime"
    output.mkdir(parents=True,exist_ok=True)
    checks=[]
    def passed(label): checks.append(label); print("PASS",label,flush=True)
    with tempfile.TemporaryDirectory(prefix="ledgerflow-live-") as temp:
        directory=Path(temp)
        proc,owner,details=start(directory)
        certificate=directory/"data/tls-cert.pem"
        try:
            assert owner.req("GET","/desktop/status")[1]["vision"]
            assert owner.req("POST","/desktop/bootstrap",{"token":details["bootstrap"]})[0]==401
            assert owner.req("POST","/auth/session",{"invite_token":"owner-demo"})[0]==404
            anonymous=Client(details["origin"],certificate)
            assert anonymous.req("GET","/workbooks")[0]==401
            no_csrf=Client(details["origin"],certificate); no_csrf.op=owner.op
            assert no_csrf.req("POST","/desktop/pairings",{"scope":"workspace"})[0]==403
            passed("TLS validates the local certificate; bootstrap is single use; demo invites and missing CSRF are refused")

            code,book,_=owner.req("POST","/workbooks",files={"file":("synthetic.xlsx",(REPO/"fixtures/synthetic/nordvik_t_accounts.xlsx").read_bytes())},fields={"display_name":"Vérification — données synthétiques"})
            assert code==202,book
            wid=book["workbook_id"]
            _,proposal,_=owner.req("POST",f"/workbooks/{wid}/mapping-proposals",{"base_version_id":book["version_id"],"base_sha256":book["sha256"]})
            _,mapping,_=owner.req("GET",f"/workbooks/{wid}/mappings/{proposal['mapping_id']}")
            code,confirmed,_=owner.req("POST",f"/workbooks/{wid}/mappings/{proposal['mapping_id']}/confirm",{"expected_mapping_version":mapping["mapping_version"],"expected_mapping_sha256":mapping["mapping_sha256"],"policy_version":"policy_nordvik_v1","confirmed_bindings":{},"baseline_acknowledgement":None})
            assert code==200,confirmed
            passed("Existing workbook inspection and mapping work through the Mac local runtime")

            code,pair,_=owner.req("POST","/desktop/pairings",{"scope":"workspace"})
            assert code==201,pair
            token=urllib.parse.urlsplit(pair["url"]).fragment
            phone=Client(details["origin"],certificate)
            code,phone_session,_=phone.req("POST","/desktop/pairings/exchange",{"token":token})
            assert code==201 and phone_session["role"]=="owner",phone_session
            phone.csrf=phone_session["csrf_token"]
            assert phone.req("GET","/workbooks")[1]["items"][0]["workbook_id"]==wid
            assert anonymous.req("POST","/desktop/pairings/exchange",{"token":token})[0]==401
            code,capture_pair,_=owner.req("POST","/desktop/pairings",{"scope":"capture"})
            assert code==201,capture_pair
            capture=Client(details["origin"],certificate)
            _,capture_session,_=capture.req("POST","/desktop/pairings/exchange",{"token":urllib.parse.urlsplit(capture_pair["url"]).fragment})
            capture.csrf=capture_session["csrf_token"]
            assert capture_session["role"]=="employee"
            passed("Full-access and capture-only phone sessions share the actual workbook; association token cannot be replayed")

            source=REPO/"fixtures/synthetic/receipts/E1.png"
            image=Image.open(source).convert("RGB")
            photo=io.BytesIO(); image.save(photo,format="JPEG",quality=94)
            photo_bytes=photo.getvalue()
            # This file is a new encoding, never recognised by the fixture SHA lookup.
            assert hashlib.sha256(photo_bytes).hexdigest()!=hashlib.sha256(source.read_bytes()).hexdigest()
            target=phone.req("GET","/upload-targets")[1]["items"][0]
            code,document,_=phone.req("POST",f"/workbooks/{wid}/documents",files={"file":("synthetic-photo.jpg",photo_bytes)},fields={"client_upload_id":"live_photo_"+uuid.uuid4().hex})
            assert code==202,document
            code,run,_=phone.req("POST","/runs",{"workbook_id":wid,"document_id":document["document_id"],"expected_base_version_id":target["base_version_id"],"expected_base_sha256":target["base_sha256"],"mapping_id":target["mapping_id"],"mapping_version":target["mapping_version"],"client_request_id":uuid.uuid4().hex})
            assert code==202,run
            rid=run["run_id"]
            snapshot=T.wait_state(owner,rid,{"AWAITING_APPROVAL","FAILED","NEEDS_REVIEW","DUPLICATE_REVIEW"},timeout=240)
            assert snapshot["state"]=="AWAITING_APPROVAL",(snapshot["state"],snapshot["state_reason"],snapshot.get("review_items"))
            assert snapshot["mock_labels"]==[],snapshot["mock_labels"]
            assert snapshot["transaction"]["gross_minor"]==125000,snapshot["transaction"]
            assert snapshot["validation_summary"]["result"]=="pass"
            assert snapshot["validation_summary"]["runtime"]=="docker"
            assert owner.req("GET","/runs")[1]["items"][0]["run_id"]==rid
            assert phone.req("GET",f"/runs/{rid}")[1]["transaction"]["gross_minor"]==125000
            passed("New JPEG read by real configured Vultr vision; generated code executes in Docker and independent verifier passes")

            approval=T.approval_body(owner,rid)
            assert capture.req("POST",f"/runs/{rid}/approval",approval)[0]==403
            assert owner.req("POST",f"/runs/{rid}/approval",{**approval,"candidate_sha256":"0"*64})[0]==409
            code,result,_=owner.req("POST",f"/runs/{rid}/approval",approval)
            assert code==200,result
            code,workbook,_=owner.req("GET",f"/artifacts/{result['commit']['artifact_id']}/download",raw=True)
            assert code==200 and hashlib.sha256(workbook).hexdigest()==result["commit"]["artifact_sha256"]
            current=Workbook(workbook); before=Workbook((REPO/"fixtures/synthetic/nordvik_t_accounts.xlsx").read_bytes())
            after_balance=baseline(current,detect_mapping(current)); before_balance=baseline(before,detect_mapping(before))
            assert after_balance["debits_minor"]-before_balance["debits_minor"]==125000
            assert after_balance["credits_minor"]-before_balance["credits_minor"]==125000
            passed("Capture-only approval and altered hash refused; exact approval commits a balanced, hash-verified XLSX")

            chat_key=uuid.uuid4().hex
            code,chat,_=owner.req("POST","/assistant/messages",{"text":"Quel document viens-tu de lire ? Donne son montant et son état actuel, sans modifier quoi que ce soit."},idem=chat_key)
            assert code==201,chat
            assert len(chat["items"])==2 and chat["items"][1].get("model"),chat
            before_count=len(owner.req("GET","/assistant/messages")[1]["items"])
            code,replayed,_=owner.req("POST","/assistant/messages",{"text":"Quel document viens-tu de lire ? Donne son montant et son état actuel, sans modifier quoi que ce soit."},idem=chat_key)
            assert code==201 and replayed==chat
            assert len(owner.req("GET","/assistant/messages")[1]["items"])==before_count
            assert phone.req("GET","/assistant/messages")[1]["items"]==owner.req("GET","/assistant/messages")[1]["items"]
            passed("Real language agent answers from the actual dossier; conversation sync and retry idempotency work")
            proc.terminate(); proc.wait(timeout=15)
            proc,restored,_=start(directory)
            saved=restored.req("GET",f"/runs/{rid}")[1]
            assert saved["state"]=="COMMITTED"
            assert len(restored.req("GET","/assistant/messages")[1]["items"])==2
            saved_bytes=restored.req("GET",f"/artifacts/{result['commit']['artifact_id']}/download",raw=True)[1]
            assert saved_bytes==workbook
            passed("Mac service restart preserves the committed run, workbook bytes and shared conversation")
            report={"scope":"local runtime, synthetic documents only; second HTTP session emulates the phone, not physical iPhone hardware","checks":checks,"run_id":rid,"model":chat["items"][1]["model"],"transaction":{"gross_minor":125000,"currency":"SEK"},"workbook_sha256":hashlib.sha256(workbook).hexdigest(),"assistant_answer":chat["items"][1]["text"],"ios_hardware_tested":False}
            (output/"live-verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        except BaseException:
            log=directory/"service.log"
            if log.exists():
                # Server diagnostics never print credentials or request bodies.
                (output/"last-failure.log").write_bytes(log.read_bytes()[-16000:])
            raise
        finally:
            if proc.poll() is None: proc.terminate(); proc.wait(timeout=15)
    print(f"{len(checks)} live integration checks passed.")


if __name__=="__main__": main()
