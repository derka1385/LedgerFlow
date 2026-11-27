"""Shared Orvect identity and a browser callback bound only to this Mac."""
import base64
import http.server
import json
from pathlib import Path
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


class AuthError(ValueError):
    pass


def client_key():
    settings = Path(__file__).resolve().parents[1] / "ios/Config/Base.xcconfig"
    match = re.search(r"^LEDGERFLOW_ORVECT_API_KEY\s*=\s*(\S+)$", settings.read_text(), re.MULTILINE)
    if not match:
        raise AuthError("AUTH_UNAVAILABLE")
    return match.group(1)


def identity_request(endpoint, payload):
    url = "https://identitytoolkit.googleapis.com/v1/accounts:" + endpoint
    query = urllib.parse.urlencode({"key": client_key()})
    request = urllib.request.Request(url + "?" + query, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=12) as reply:
            return json.load(reply)
    except urllib.error.HTTPError as error:
        if error.code >= 500:
            raise AuthError("AUTH_UNAVAILABLE") from None
        raise AuthError("LOGIN_INVALID") from None
    except (OSError, ValueError):
        raise AuthError("AUTH_UNAVAILABLE") from None


def verified_account(token):
    if not isinstance(token, str) or not 64 <= len(token) <= 8192:
        raise AuthError("LOGIN_INVALID")
    users = identity_request("lookup", {"idToken": token}).get("users", [])
    if not users or not users[0].get("localId"):
        raise AuthError("LOGIN_INVALID")
    account = users[0]
    if not account.get("emailVerified"):
        raise AuthError("EMAIL_UNVERIFIED")
    return {"uid": account["localId"], "name": account.get("displayName") or account.get("email") or "My workspace"}


def password_account(email, password):
    result = identity_request("signInWithPassword", {"email": email, "password": password, "returnSecureToken": True})
    return verified_account(result.get("idToken"))


_BROWSER_PAGE = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in to LedgerFlow</title>
<style>
body{font:16px system-ui;background:#102e25;color:#f0f4e5;margin:0;padding:clamp(30px,12vw,130px)}
main{max-width:480px;margin:auto}h1{font:normal 42px Georgia;margin:.5em 0}
button{display:inline-flex;align-items:center;gap:10px;min-height:40px;padding:8px 12px;background:#fff;color:#1f1f1f;border:1px solid #747775;border-radius:6px;font:500 14px/20px system-ui;cursor:pointer}
button img{object-fit:contain}
</style>
<main><h1>Sign in to LedgerFlow</h1><p>Use the Google account you use with Orvect.</p>
<button id="google" disabled><img src="data:image/png;base64,__GOOGLE_G__" alt="" width="18" height="18">Continue with Google</button><p id="result" role="status"></p></main>
<script type="module" nonce="__NONCE__">
import {initializeApp} from "https://www.gstatic.com/firebasejs/12.2.1/firebase-app.js";
import {getAuth, GoogleAuthProvider, inMemoryPersistence, setPersistence, signInWithPopup}
  from "https://www.gstatic.com/firebasejs/12.2.1/firebase-auth.js";
const auth = getAuth(initializeApp({apiKey: __KEY__, authDomain: "orvect.firebaseapp.com", projectId:"orvect"}));
const button = document.getElementById("google"), status = document.getElementById("result");
try {
  await setPersistence(auth, inMemoryPersistence);
  button.disabled = false;
} catch {
  status.textContent = "This browser could not start Google sign-in.";
}
button.onclick = async () => {
  button.disabled = true;
  status.textContent = "Waiting for Google…";
  try {
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({prompt:"select_account"});
    const credential = await signInWithPopup(auth, provider);
    const response = await fetch(location.pathname, {
      method: "POST", headers: {"Content-Type":"application/json"}, credentials: "omit",
      body: JSON.stringify({idToken: await credential.user.getIdToken()})
    });
    if (!response.ok) throw new Error("bridge");
    status.textContent = "Signed in. Return to LedgerFlow.";
    button.hidden = true;
  } catch (error) {
    status.textContent = error.code === "auth/popup-blocked" ? "Allow the Google sign-in window and try again."
      : error.code === "auth/account-exists-with-different-credential" ? "Use the sign-in method already linked to your Orvect account."
      : "Sign-in could not be completed. Try again or return to LedgerFlow.";
    button.disabled = false;
  }
};
</script></html>"""


class GoogleBroker:
    def __init__(self):
        self.lock = threading.Lock()
        self.flows = {}
        self.server = None

    def begin(self, has_launch_proof):
        with self.lock:
            self.flows = {key: flow for key, flow in self.flows.items() if flow["expires"] > time.monotonic()}
            if len(self.flows) >= 12:
                raise AuthError("LOGIN_THROTTLED")
            if not self.server:
                self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
                threading.Thread(target=self.server.serve_forever, daemon=True).start()
            browser = secrets.token_urlsafe(32)
            poll = secrets.token_urlsafe(32)
            self.flows[browser] = {"poll": poll, "expires": time.monotonic() + 300, "launch": has_launch_proof, "identity": None}
            return {"url": f"http://localhost:{self.server.server_port}/ledgerflow-google/{browser}", "poll": poll}

    def poll(self, token):
        with self.lock:
            entry = next(((key, flow) for key, flow in self.flows.items() if secrets.compare_digest(flow["poll"], token)), None)
            if not entry or entry[1]["expires"] <= time.monotonic():
                raise AuthError("GOOGLE_EXPIRED")
            key, flow = entry
            if not flow["identity"]:
                return None
            del self.flows[key]
            return flow["identity"], flow["launch"]

    def _handler(self):
        broker = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def reply(self, status, body=b"", nonce=None):
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cross-Origin-Opener-Policy", "same-origin-allow-popups")
                self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; "
                    f"script-src 'nonce-{nonce}' https://www.gstatic.com https://apis.google.com; style-src 'unsafe-inline'; img-src data:; "
                    "frame-src https://orvect.firebaseapp.com; connect-src 'self' https://www.googleapis.com "
                    "https://identitytoolkit.googleapis.com https://securetoken.googleapis.com https://orvect.firebaseapp.com")
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def flow_key(self):
                if self.headers.get("Host") != f"localhost:{self.server.server_port}":
                    return None
                match = re.fullmatch(r"/ledgerflow-google/([A-Za-z0-9_-]{43})", self.path)
                return match.group(1) if match else None

            def do_GET(self):
                key = self.flow_key()
                with broker.lock:
                    flow = broker.flows.get(key)
                    if not flow or flow["expires"] <= time.monotonic():
                        return self.reply(404)
                nonce = secrets.token_urlsafe(18)
                logo = Path(__file__).resolve().parents[2] / "frontend/public/icons/google-g.png"
                page = (_BROWSER_PAGE.replace("__NONCE__", nonce).replace("__KEY__", json.dumps(client_key()))
                        .replace("__GOOGLE_G__", base64.b64encode(logo.read_bytes()).decode("ascii")))
                self.reply(200, page.encode(), nonce)

            def do_POST(self):
                key = self.flow_key()
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    return self.reply(400)
                if not key or self.headers.get("Origin") != f"http://localhost:{self.server.server_port}" or not 0 < size < 10000:
                    return self.reply(403)
                with broker.lock:
                    flow = broker.flows.get(key)
                    if not flow or flow["expires"] <= time.monotonic() or flow["identity"]:
                        return self.reply(404)
                try:
                    self.connection.settimeout(5)
                    body = json.loads(self.rfile.read(size))
                    identity = verified_account(body.get("idToken") if isinstance(body, dict) else None)
                except (AuthError, UnicodeError, json.JSONDecodeError, OSError):
                    return self.reply(401)
                with broker.lock:
                    flow = broker.flows.get(key)
                    if not flow or flow["expires"] <= time.monotonic() or flow["identity"]:
                        return self.reply(404)
                    flow["identity"] = identity
                self.reply(204)

        return Handler
