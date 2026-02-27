# RUN

## 1) Install dependencies

```bash
cd /Users/chehaotian/TrustRAG/medrag-spdz
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn
```

## 2) Start backend

```bash
cd /Users/chehaotian/TrustRAG/medrag-spdz
source .venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

## 3) Quick check

```bash
curl http://127.0.0.1:8000/docs
curl http://127.0.0.1:8000/doc/doc1
```
