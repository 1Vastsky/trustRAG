# RUN

## 1) Python dependencies

```bash
cd /Users/chehaotian/TrustRAG/trustRAG
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn httpx pytest py-ecc web3 eth-account eth-abi eth-tester py-evm
```

## 2) Node/Hardhat dependencies

```bash
cd /Users/chehaotian/TrustRAG/trustRAG
npm install --cache .npm-cache
```

## 3) Start document backend

```bash
cd /Users/chehaotian/TrustRAG/trustRAG
source .venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

## 4) Quick API check

```bash
curl http://127.0.0.1:8000/docs
curl http://127.0.0.1:8000/doc/doc1
```

## 5) Run tests

```bash
cd /Users/chehaotian/TrustRAG/trustRAG
source .venv/bin/activate
PYTHONPATH=. python3 -m pytest -q
```

## 6) Compile contract

```bash
cd /Users/chehaotian/TrustRAG/trustRAG
npx hardhat compile
```

## 7) Run full simulation

```bash
cd /Users/chehaotian/TrustRAG/trustRAG
source .venv/bin/activate
PYTHONPATH=. python3 scripts/simulate.py
```
