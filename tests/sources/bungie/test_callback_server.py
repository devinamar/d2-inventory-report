# Tests for the local end of the Bungie login (sources/bungie/callback_server.py):
# the self-signed certificate, and the HTTPS server on localhost that catches
# Bungie's redirect. webbrowser.open is a stand-in that plays the browser.
import socket
import ssl
import threading
import urllib.error
import urllib.request

import pytest
from cryptography import x509

import paths
from sources.bungie import callback_server

LOGIN = 'https://bungie.example/login'


@pytest.fixture(autouse=True)
def certificate_files(tmp_path, monkeypatch):
    # The certificate and its key in this test's own folder.
    monkeypatch.setattr(paths, 'OAUTH_CERT_FILE', tmp_path / 'cert.pem')
    monkeypatch.setattr(paths, 'OAUTH_KEY_FILE', tmp_path / 'key.pem')


def free_port():
    with socket.socket() as s:
        s.bind(('localhost', 0))
        return s.getsockname()[1]


# The certificate


def test_the_certificate_covers_localhost_and_its_key_is_owner_only():
    callback_server.ensure_certificate()
    cert = x509.load_pem_x509_certificate(paths.OAUTH_CERT_FILE.read_bytes())
    names = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert names.get_values_for_type(x509.DNSName) == ['localhost']
    assert [str(ip) for ip in names.get_values_for_type(x509.IPAddress)] == ['127.0.0.1']
    assert paths.OAUTH_KEY_FILE.stat().st_mode & 0o777 == 0o600


def test_an_existing_certificate_is_reused():
    # A browser keeps the exception made for it.
    callback_server.ensure_certificate()
    first = (paths.OAUTH_CERT_FILE.read_bytes(), paths.OAUTH_KEY_FILE.read_bytes())
    callback_server.ensure_certificate()
    assert (paths.OAUTH_CERT_FILE.read_bytes(), paths.OAUTH_KEY_FILE.read_bytes()) == first


# The server


def test_the_redirect_query_comes_back_and_other_paths_get_404(monkeypatch):
    port = free_port()
    client = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    client.check_hostname = False
    client.verify_mode = ssl.CERT_NONE  # the certificate is self-signed
    statuses, visits, opened = [], [], []

    def visit():
        # Stands in for the browser: a stray request, then Bungie's redirect.
        for path in ('/favicon.ico', '/callback?code=abc&state=xyz'):
            url = f'https://localhost:{port}{path}'
            try:
                statuses.append(urllib.request.urlopen(url, context=client, timeout=5).status)
            except urllib.error.HTTPError as e:
                statuses.append(e.code)

    def open_browser(url):
        opened.append(url)
        visits.append(threading.Thread(target=visit))
        visits[0].start()

    monkeypatch.setattr(callback_server.webbrowser, 'open', open_browser)
    params = callback_server.open_and_wait(LOGIN, f'https://localhost:{port}/callback', timeout=10)
    visits[0].join(5)
    assert opened == [LOGIN]
    assert params == {'code': 'abc', 'state': 'xyz'}
    assert statuses == [404, 200]


def test_nothing_arriving_returns_an_empty_query_after_the_timeout(monkeypatch):
    opened = []
    monkeypatch.setattr(callback_server.webbrowser, 'open', opened.append)
    redirect = f'https://localhost:{free_port()}/callback'
    assert callback_server.open_and_wait(LOGIN, redirect, timeout=1) == {}
    assert opened == [LOGIN]


def test_a_busy_port_raises_before_the_browser_opens(monkeypatch):
    opened = []
    monkeypatch.setattr(callback_server.webbrowser, 'open', opened.append)
    with socket.socket() as taken:
        taken.bind(('localhost', 0))
        taken.listen()
        redirect = f'https://localhost:{taken.getsockname()[1]}/callback'
        with pytest.raises(OSError):
            callback_server.open_and_wait(LOGIN, redirect)
    assert opened == []
