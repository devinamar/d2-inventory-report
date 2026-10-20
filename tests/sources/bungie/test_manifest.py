# Tests for downloading the manifest (sources/bungie/manifest.py) into a cache
# folder under tmp_path. A stand-in API names the current version, and the
# download is a zip holding the SQLite file, built in memory.
import io
import types
import zipfile

import pytest
import requests

import paths
from sources.bungie import manifest
from tests import conftest as c

CONTENT_PATH = '/common/destiny2_content/sqlite/en/world_sql_content_{}.content'


@pytest.fixture
def cache(tmp_path, monkeypatch):
    # The manifest cache folder, holding an older version.
    folder = tmp_path / 'manifest'
    folder.mkdir()
    (folder / 'world_sql_content_old.sqlite').write_bytes(b'old')
    monkeypatch.setattr(paths, 'MANIFEST_CACHE_DIR', folder)
    return folder


def bungie(version):
    # The API client, as far as download_manifest uses it.
    return types.SimpleNamespace(
        get_manifest=lambda: {'mobileWorldContentPaths': {'en': CONTENT_PATH.format(version)}}
    )


def serve(monkeypatch, body):
    # Swap requests.get for Bungie's download server answering body; returns
    # the (url, timeout, stream) of each request.
    sent = []

    def get(url, timeout, stream):
        sent.append((url, timeout, stream))
        return c.make_response(body=body)

    monkeypatch.setattr(manifest.requests, 'get', get)
    return sent


def zipped(data):
    # A zip holding one file, the way Bungie serves the manifest.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('world_sql_content_new.content', data)
    return buffer.getvalue()


def test_a_cached_version_is_used_without_downloading(cache, monkeypatch):
    (cache / 'world_sql_content_new.sqlite').write_bytes(b'cached')
    monkeypatch.delattr(manifest.requests, 'get')  # any download would fail the test
    assert manifest.download_manifest(bungie('new')) == (
        cache / 'world_sql_content_new.sqlite',
        'world_sql_content_new',
    )


def test_a_new_version_is_downloaded_unzipped_and_older_ones_deleted(cache, monkeypatch):
    sent = serve(monkeypatch, zipped(b'SQLite format 3\x00new'))
    path, version = manifest.download_manifest(bungie('new'))
    assert (path, version) == (cache / 'world_sql_content_new.sqlite', 'world_sql_content_new')
    assert path.read_bytes() == b'SQLite format 3\x00new'
    assert sent == [(f'https://www.bungie.net{CONTENT_PATH.format("new")}', 120, True)]
    # No .part file is left behind.
    assert [p.name for p in cache.iterdir()] == ['world_sql_content_new.sqlite']


def test_a_broken_download_leaves_no_manifest_behind(cache, monkeypatch):
    # The older version stays until a new one is in place.
    serve(monkeypatch, b'<html>')
    with pytest.raises(zipfile.BadZipFile):
        manifest.download_manifest(bungie('new'))
    assert [p.name for p in cache.iterdir()] == ['world_sql_content_old.sqlite']


def test_a_download_cut_off_midway_leaves_no_part_file(cache, monkeypatch):
    # The connection drops after the first chunk of the zip; the older version
    # stays, and the next run starts over.
    def iter_content(response, chunk_size):
        yield response.raw.read(chunk_size)
        raise requests.exceptions.ChunkedEncodingError('Connection broken')

    serve(monkeypatch, zipped(bytes(100_000)))
    monkeypatch.setattr(requests.Response, 'iter_content', iter_content)
    with pytest.raises(requests.exceptions.ChunkedEncodingError):
        manifest.download_manifest(bungie('new'))
    assert [p.name for p in cache.iterdir()] == ['world_sql_content_old.sqlite']
