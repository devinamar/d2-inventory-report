# The local end of the Bungie login: a one-shot HTTPS server on the redirect
# URI's port that catches the browser when Bungie sends it back with the login
# code, plus the self-signed certificate that server needs. Bungie only accepts
# https:// redirect URIs, even to localhost, so plain HTTP won't do.
#
# DEV NOTE: Ive opted for verbose comments in this section to
# assist future me in understanding oauth processes.

import datetime
import http.server
import ipaddress
import ssl
import time
import urllib.parse
import webbrowser

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

import paths

# The page the browser shows once Bungie sends it back. The terminal reports
# whether the login worked, so the page only says where to look.
PAGE = b"""<!DOCTYPE html>
<html>
  <head><title>Bungie login</title></head>
  <body style="font-family: system-ui, sans-serif; background: #1a1a1a; color: #d0d0d0;
               display: grid; place-items: center; height: 100vh; margin: 0">
    <p>Bungie login received. You can close this tab and return to the terminal.</p>
  </body>
</html>"""


def ensure_certificate() -> None:
    # Generate the self-signed TLS certificate and key for localhost, unless
    # they already exist. Valid for 10 years and covers both "localhost" and
    # 127.0.0.1. Browsers warn about a self-signed certificate the first
    # time; click through once and the exception sticks for the lifetime of
    # the certificate.
    if paths.OAUTH_CERT_FILE.exists() and paths.OAUTH_KEY_FILE.exists():
        return

    # 2048-bit RSA keypair. 65537 is the standard public exponent: small
    # enough for fast verification, large enough for security. 2048 bits is
    # the current practical minimum.
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # In a real CA chain, subject = who the cert is FOR and issuer = who
    # SIGNED it. Self-signed means the two are the same identity, so we
    # reuse one x509.Name object. CN=localhost is a legacy identifier
    # (modern browsers ignore CN and look at Subject Alt Name below).
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])

    now = datetime.datetime.now(datetime.UTC)
    cert = (
        # Fluent builder: each call returns a new builder with that field
        # set. The final .sign() produces the Certificate object.
        x509.CertificateBuilder()
        # Who the cert certifies (identity), and who signed it: the same for
        # a self-signed cert.
        .subject_name(subject)
        .issuer_name(issuer)
        # The public half of our RSA keypair gets baked into the cert. The
        # private key stays separate and never leaves disk.
        .public_key(key.public_key())
        # Unique ID for this cert, random because there's no CA to
        # coordinate serial numbers with.
        .serial_number(x509.random_serial_number())
        # Validity window. The -5 minutes absorbs small clock differences
        # between this machine and whatever checks the cert. 3650 days is
        # far beyond normal cert hygiene, but this is a localhost cert, not a
        # public one: we want "generate once, forget", not "renew every 90
        # days".
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=3650))
        # Subject Alternative Name: how browsers decide which hostnames a
        # cert covers. It must list every name the server is reached by: the
        # redirect uses "localhost", and 127.0.0.1 is the same machine.
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        # Self-sign with the private key, hashing with SHA-256. SHA-1 has
        # been deprecated for cert signing since ~2017.
        .sign(key, hashes.SHA256())
    )

    # The private key must never be readable by other users, even briefly.
    # touch(mode=0o600) creates the file with owner-only read/write before
    # anything is in it; write_bytes then fills it and leaves the permissions
    # alone. Writing directly would create the file with the default
    # permissions (often world-readable 0o644) first.
    paths.OAUTH_KEY_FILE.touch(mode=0o600)
    paths.OAUTH_KEY_FILE.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    paths.OAUTH_CERT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


class CallbackServer(http.server.HTTPServer):
    # An HTTPServer that also holds the login's state. Each Handler reaches
    # its server through self.server, so the handler reads redirect_path
    # from here and leaves the query it caught in received.
    redirect_path: str
    received: dict | None = None


class Handler(http.server.BaseHTTPRequestHandler):
    # http.server creates one Handler per browser request and calls its
    # do_GET. Whatever do_GET returns is thrown away, so the result goes on
    # the server instead. The annotation tells type checkers that
    # self.server is always a CallbackServer; http.server only declares a
    # generic server, so pyright needs the ignore.
    server: CallbackServer  # pyright: ignore[reportIncompatibleVariableOverride]

    def do_GET(self):  # noqa: N802 (name set by http.server)
        url = urllib.parse.urlparse(self.path)
        if url.path != self.server.redirect_path:
            self.send_error(404)  # e.g. the browser asking for a favicon
            return
        self.server.received = dict(urllib.parse.parse_qsl(url.query))
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, format, *args):  # noqa: ARG002 (signature set by http.server)
        pass  # keep http.server's per-request log lines out of the terminal


def open_and_wait(login_url: str, redirect_uri: str, timeout: int = 300) -> dict:
    # Start the HTTPS server on the redirect URI's host and port, open
    # login_url in the browser, and wait for Bungie to send the browser back
    # to the redirect URI's path. Returns that request's query parameters
    # ({name: value}, e.g. code and state), or {} when nothing arrives within
    # timeout seconds. Raises OSError when the port can't be opened.
    redirect = urllib.parse.urlparse(redirect_uri)

    # Bind first, then open the browser, so a fast redirect can't arrive
    # before anything is listening. wrap_socket makes every accepted
    # connection speak TLS with our certificate.
    ensure_certificate()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(paths.OAUTH_CERT_FILE, paths.OAUTH_KEY_FILE)
    server = CallbackServer((redirect.hostname or 'localhost', redirect.port or 443), Handler)
    server.redirect_path = redirect.path
    server.socket = context.wrap_socket(server.socket, server_side=True)
    webbrowser.open(login_url)

    # handle_request() serves one connection, or returns once server.timeout
    # passes without one. A failed TLS handshake (the first-run certificate
    # warning) and a favicon request are connections too, so loop until the
    # redirect itself arrives or the time is up.
    deadline = time.monotonic() + timeout
    with server:
        while server.received is None and time.monotonic() < deadline:
            server.timeout = deadline - time.monotonic()
            server.handle_request()
    return server.received or {}
