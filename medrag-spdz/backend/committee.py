"""Committee node service for collecting Shamir shares."""

from __future__ import annotations

import os
from typing import Dict

from fastapi import FastAPI
from pydantic import BaseModel, Field

from backend.shamir import DEFAULT_PRIME
from backend.spdz_runner import run_spdz_pair

NODE_ID = os.getenv("COMMITTEE_NODE_ID", "unknown")

app = FastAPI(
    title=f"Committee Node {NODE_ID}",
    version="0.1.0",
    docs_url="/api-docs",
    redoc_url="/redoc",
)

# shares[rid][doc_id][voter_id] = {"s_share": {"x": int, "y": int}, "r_share": {...}}
shares: Dict[int, Dict[str, Dict[str, Dict[str, Dict[str, int]]]]] = {}


class SharePoint(BaseModel):
    x: int = Field(..., ge=1)
    y: int


class SharePayload(BaseModel):
    rid: int = Field(..., ge=1)
    doc_id: str = Field(..., min_length=1)
    voter_id: str = Field(..., min_length=1)
    s_share: SharePoint
    r_share: SharePoint


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "node_id": NODE_ID}


@app.post("/share")
def submit_share(payload: SharePayload) -> Dict[str, object]:
    rid_bucket = shares.setdefault(payload.rid, {})
    doc_bucket = rid_bucket.setdefault(payload.doc_id, {})
    doc_bucket[payload.voter_id] = {
        "s_share": {"x": payload.s_share.x, "y": payload.s_share.y},
        "r_share": {"x": payload.r_share.x, "y": payload.r_share.y},
    }
    return {
        "ok": True,
        "node_id": NODE_ID,
        "rid": payload.rid,
        "doc_id": payload.doc_id,
        "voter_id": payload.voter_id,
        "stored_count": len(doc_bucket),
    }


@app.get("/shares/{rid}/{doc_id}")
def get_shares(rid: int, doc_id: str) -> Dict[str, object]:
    doc_bucket = shares.get(rid, {}).get(doc_id, {})
    return {
        "node_id": NODE_ID,
        "rid": rid,
        "doc_id": doc_id,
        "count": len(doc_bucket),
        "voter_ids": sorted(doc_bucket.keys()),
        "shares": doc_bucket,
    }


@app.post("/trigger/{rid}/{doc_id}")
def trigger_aggregation(rid: int, doc_id: str) -> Dict[str, object]:
    doc_bucket = shares.get(rid, {}).get(doc_id, {})
    if not doc_bucket:
        return {
            "node_id": NODE_ID,
            "rid": rid,
            "doc_id": doc_id,
            "status": "no shares",
            "stored_count": 0,
        }

    x_values = set()
    s_values = []
    r_values = []
    for item in doc_bucket.values():
        sx = item["s_share"]["x"]
        rx = item["r_share"]["x"]
        if sx != rx:
            return {
                "node_id": NODE_ID,
                "rid": rid,
                "doc_id": doc_id,
                "status": "error",
                "error": "s_share.x and r_share.x mismatch",
            }
        x_values.add(sx)
        s_values.append(item["s_share"]["y"])
        r_values.append(item["r_share"]["y"])

    if len(x_values) != 1:
        return {
            "node_id": NODE_ID,
            "rid": rid,
            "doc_id": doc_id,
            "status": "error",
            "error": "inconsistent share x values in node storage",
        }

    x = x_values.pop()
    s_total, r_total = run_spdz_pair(s_values=s_values, r_values=r_values, p=DEFAULT_PRIME)
    return {
        "node_id": NODE_ID,
        "rid": rid,
        "doc_id": doc_id,
        "status": "ok",
        "stored_count": len(doc_bucket),
        "share": {"x": x, "s_y": s_total, "r_y": r_total},
        "field_prime": DEFAULT_PRIME,
    }
