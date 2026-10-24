# Tests for fetching d2-perk-popularity's scores (sources/perk_popularity.py),
# with requests.get swapped for a stand-in answering as GitHub's raw file host
# does: JSON served as text/plain, and a 404 while the repo is private.
import pytest
import requests

from sources import perk_popularity
from tests import conftest as c

TEXT = {'Content-Type': 'text/plain; charset=utf-8'}


def answer(monkeypatch, response):
    # Swap requests.get for one answering response; returns what it was sent.
    sent = []

    def get(url, timeout):
        sent.append((url, timeout))
        return response

    monkeypatch.setattr(perk_popularity.requests, 'get', get)
    return sent


def test_the_scores_file_is_fetched_from_the_data_branch(monkeypatch):
    scores = {'generated_at': '2026-10-23T23:51:33Z', 'pve': [], 'pvp': []}
    sent = answer(monkeypatch, c.make_response(payload=scores, headers=TEXT))
    assert perk_popularity.fetch_scores() == scores
    assert sent == [(perk_popularity.SCORES_URL, 30)]


def test_a_private_repo_raises(monkeypatch):
    # GitHub's reply on 2026-10-23, while the repo was private.
    answer(monkeypatch, c.make_response(status=404, body=b'404: Not Found', headers=TEXT))
    with pytest.raises(requests.HTTPError):
        perk_popularity.fetch_scores()
