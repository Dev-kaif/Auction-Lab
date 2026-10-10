# AuctionLab: Game Theory & Data Science Simulator

AuctionLab is a four-advertiser game theory simulator with one focused workspace for manual auctions and
automatic experiments. It includes first-price and second-price mechanisms, data visualizations, and
SQLite-backed experiment history with CSV export. Read the [backend guide](backend/README.md) for API,
auction formulas, simulation metrics, persistence, and CSV details; read the [frontend guide](frontend/README.md)
for the workspace, request flow, charts, and responsive behavior.

## Run locally
Backend (Python 3.11+), in terminal 1:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000     # API docs: http://localhost:8000/docs
```

Frontend (Node 18+), in terminal 2:

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (proxies /api to :8000)
```

SQLite defaults to `./auctionlab.db` in the backend working directory. Set `AUCTIONLAB_DATABASE_URL`
to use another SQLAlchemy URL, for example `sqlite:////absolute/path/auctionlab.db`. Tables are
initialized idempotently when the API starts or first handles a database request.

## Tests
```bash
cd backend && python -m pytest        # engine + API + persistence
cd frontend && npm test               # all frontend tests
```

## Workspace

Choose the auction mechanism and Manual or Automatic mode in the workspace. Manual mode edits valuations
and bids for A, B, C, and D, then displays backend-calculated ranking, payment, revenue, and payoffs.
Automatic mode compares selected bidding-fraction profiles over repeated auctions and shows an aggregate
revenue chart, result metrics, and optional supporting analysis. The backend reuses the same valuation
scenarios across profiles and mechanisms in a run. The resolved seed is shown with results. Fixed-value
scenarios repeat the same valuation vector on every auction and are deterministic.

Completed manual auctions and simulations are saved in SQLite. Use Experiment History in the workspace
header to reopen configuration/results, download CSV, or delete records. The sweep endpoint is an analysis
request and does not create a history record. API docs (Swagger): http://localhost:8000/docs.
