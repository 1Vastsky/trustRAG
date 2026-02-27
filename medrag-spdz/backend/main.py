"""FastAPI backend for document loading and lookup."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException

BASE_DIR = Path(__file__).resolve().parent
DOCS_CSV = BASE_DIR / "docs.csv"

app = FastAPI(
    title="MedRAG-SPDZ Backend",
    version="0.1.0",
    docs_url="/api-docs",
    redoc_url="/redoc",
)


def load_docs() -> List[Dict[str, str]]:
    """Load all docs from CSV with columns: doc_id,text."""
    docs: List[Dict[str, str]] = []
    with DOCS_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            doc_id = (row.get("doc_id") or "").strip()
            text = row.get("text") or ""
            if doc_id:
                docs.append({"doc_id": doc_id, "text": text})
    return docs


@app.get("/docs")
def list_docs() -> Dict[str, List[Dict[str, str]]]:
    return {"docs": load_docs()}


@app.get("/doc/{doc_id}")
def get_doc(doc_id: str) -> Dict[str, str]:
    for doc in load_docs():
        if doc["doc_id"] == doc_id:
            return doc
    raise HTTPException(status_code=404, detail=f"doc_id '{doc_id}' not found")
