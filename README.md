# AuctionLab

AuctionLab is an educational game theory simulator for exploring single-item auctions. Compare first-price and second-price rules using four advertisers (A, B, C, and D), either by entering valuations and bids yourself or by running automatic simulations. Results come from the auction engine and include payments, payoffs, revenue, and strategy comparisons. Completed experiments are saved locally in SQLite and can be revisited or exported as CSV.

## Run with Docker

From the repository root, start the app with Docker Compose:

```bash
docker compose up --build
```

Open the app at <http://localhost:8080>. The API is at <http://localhost:8000>, with interactive documentation at <http://localhost:8000/docs>. Experiment data is kept in a Docker volume when containers stop or are rebuilt.

Stop the app with `Ctrl+C`. You can also run `docker compose down` to stop and remove the containers while keeping experiment data. To remove the data volume too, run:

```bash
docker compose down --volumes
```

To use a different web port, set `AUCTIONLAB_WEB_PORT`, for example:

```bash
AUCTIONLAB_WEB_PORT=8090 docker compose up --build
```

## Run locally without Docker

You need Python 3.11+ and Node.js 18+. Start the backend in one terminal:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Then start the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the frontend URL printed by Vite (typically <http://localhost:5173>). It proxies API requests to the backend on port 8000.

## Tests

Run the backend and frontend test suites from their respective directories:

```bash
cd backend && python -m pytest
cd frontend && npm test
```

## More documentation

- [Backend guide](backend/README.md): auction rules and formulas, API, simulation metrics, SQLite persistence, and CSV exports.
- [Frontend guide](frontend/README.md): workspace structure, API usage, charts, and interface behavior.
