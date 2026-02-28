"""Tests for committee share collection service."""

from fastapi.testclient import TestClient

from backend import committee


def setup_function() -> None:
    committee.shares.clear()


def test_share_submission_and_query() -> None:
    client = TestClient(committee.app)

    payload = {
        "rid": 1,
        "doc_id": "doc1",
        "voter_id": "v1",
        "s_share": {"x": 1, "y": 123},
        "r_share": {"x": 1, "y": 456},
    }
    r_post = client.post("/share", json=payload)
    assert r_post.status_code == 200
    assert r_post.json()["stored_count"] == 1

    r_get = client.get("/shares/1/doc1")
    assert r_get.status_code == 200
    body = r_get.json()
    assert body["count"] == 1
    assert body["voter_ids"] == ["v1"]
    assert body["shares"]["v1"]["s_share"]["y"] == 123

    r_trigger = client.post("/trigger/1/doc1")
    assert r_trigger.status_code == 200
    assert r_trigger.json()["status"] == "not implemented"
