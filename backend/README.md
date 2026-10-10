# AuctionLab backend

FastAPI service for AuctionLab's four-advertiser single-slot and multi-slot auction simulator. This service is the source of truth for allocation, prices, expected utilities, simulation metrics, and saved experiment records. The React app calls it through the `/api` routes.

## Run locally

Requires Python 3.11 or newer. From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

The interactive API documentation is at <http://localhost:8000/docs>; health check: `GET /api/health`.
SQLite defaults to `./auctionlab.db`, relative to the backend process working directory. Configure another SQLAlchemy database URL with `AUCTIONLAB_DATABASE_URL`, for example `sqlite:////absolute/path/auctionlab.db`. Configure browser origins with `AUCTIONLAB_CORS_ORIGINS` as a comma-separated list. The default permits the Vite development URLs on port 5173.

Run backend tests from `backend/` with `python -m pytest`.

The repository-root Docker Compose setup builds this service together with the frontend. In the container,
SQLite is stored at `/data/auctionlab.db` on the named `auctionlab_data` volume, so rebuilding images does
not remove saved experiments. See the root README for the one-command launch instructions.

## What the backend does

`app/main.py` creates the FastAPI app, configures CORS and error responses, initializes the database at startup, and mounts the auction, simulation, and experiment routers. Pydantic schemas validate HTTP inputs and describe responses. The auction engine under `app/auctions/` has no dependency on FastAPI; simulation uses a vectorized NumPy engine in `app/simulation/` which mirrors the same rules. `app/analytics/metrics.py` summarizes completed simulation batches. `app/experiments.py` saves and reads experiment records and builds CSV output.

The four advertisers are always ordered A, B, C, D. First-price and second-price experiments retain the original single-slot model. GSP and VCG allocate up to four ordered ad slots, with three positions and CTRs `(1.00, 0.70, 0.40)` by default. These are illustrative position-based click-through rates, not empirical predictions; real CTR depends on advertiser, creative, query, device, and other factors. Inputs are non-negative values up to ₹1,000,000 with two decimal places and represent rupees per click in multi-slot runs. The exact engine converts money to `Decimal` and rounds to paise using half-up rounding. Batch simulation uses NumPy rounding to two decimals (ties to even), so half-paise boundaries can differ between exact and batch paths.

## Auction rules and formulas

Let advertiser `i` have private valuation `v_i` and submit bid `b_i`. The winner is the highest bidder:

\[
w = \operatorname*{arg\,max}_{i\in\{A,B,C,D\}} b_i.
\]

If multiple advertisers share the highest bid, the lowest index wins: A, then B, then C, then D. Ranks are sorted by bid descending with the same tie order. The runner-up bid is the highest bid among bidders other than the winner; if the top bid is tied, it equals the winning bid.

For first-price:

\[
p_w=b_w,\qquad p_i=0\ (i\ne w).
\]

For second-price:

\[
p_w=\max_{j\ne w}b_j,\qquad p_i=0\ (i\ne w).
\]

Payoffs use true values, not submitted bids, and losing bidders receive zero:

\[
u_i = \begin{cases}v_i-p_i & i=w\\0 & i\ne w.\end{cases}
\]

The platform's revenue is total payment, `R = Σ_i p_i` (only one payment can be nonzero). For example, with values `(100, 80, 60, 40)` and bids `(90, 80, 60, 40)`, A wins. First-price payment/revenue is ₹90 and A's payoff is ₹10. Second-price payment/revenue is ₹80 and A's payoff is ₹20. B, C, and D have zero payoff in either case. This is only an example; the API computes each response from the submitted inputs.

The model assumes private values and quasilinear utility (value less payment), with no budget constraints, quality scores, reserve price, or advertiser-specific CTRs. Tie-breaking is deterministic, so the same inputs always produce the same one-auction output.

## Multi-slot GSP and VCG

For GSP and VCG, values and bids are rupees per click. Advertisers are ranked by bid descending, with ties resolved A → B → C → D, and assigned at most one slot each. A `click_through_rates` vector must contain one to four finite values in `[0, 1]` and be non-increasing. It defaults to `[1.0, 0.7, 0.4]`; advertisers below the last configured slot are unallocated.

For advertiser `i` in slot `s`, expected value is `CTRₛ × vᵢ` rupees per impression. Expected utility is expected value minus expected payment, and platform revenue is the sum of expected payments. Social welfare is the sum of `CTRₛ × true value` across allocated advertisers.

- **GSP:** each allocated advertiser pays the next-ranked bid per click. Expected payment per impression is `CTRₛ × next bid`; a final bidder with no bidder below them pays zero.
- **VCG:** slots are allocated by bids. Each advertiser's expected payment is the welfare of all *other* advertisers in the best allocation without them, minus the welfare those others receive in the actual allocation. The API also reports an effective per-click price (expected payment divided by CTR, or zero for a zero-CTR slot).

VCG externalities use submitted bids, while actual utility uses true value. Truthful bids therefore produce a welfare-maximizing allocation in this model. The model allows at most one click opportunity per slot per impression. It omits quality scores, budgets, reserves, and other rules found in real ad platforms.

The exact auction path is the source of truth for a single manual run. Repeated simulations use a separate vectorized NumPy implementation for performance; it implements the same allocation, payment, utility, and tie rules on its rounded batch values. Request validation and response serialization live at the API boundary, not in the auction engine. The UI should treat these response fields as calculated results and should not substitute browser-side estimates.

## API routes

All JSON validation errors use status 422 and an envelope like `{"error":{"code":"validation_error","message":"...","details":[...]}}`. Missing saved experiment IDs return 404. Reusing an idempotency key for a different request returns 409.

### `POST /api/auctions/run`

Runs and persists one completed manual auction. Request fields:

```json
{
  "mechanism": "first_price",
  "valuations": [100, 80, 60, 40],
  "bids": [90, 80, 60, 40]
}
```

`mechanism` is `first_price`, `second_price`, `gsp`, or `vcg`; each value and bid vector must contain exactly four finite numbers. `click_through_rates` is optional and defaults to `[1.0, 0.7, 0.4]`. All responses contain the original single-slot fields for compatibility. Multi-slot advertiser rows additionally report `slot`, `click_through_rate`, `payment_per_click`, `expected_value`, `expected_payment`, and `expected_utility`; the response also includes `social_welfare` and `is_multi_slot`. In multi-slot output, `won` means the advertiser received a slot, while `winner` identifies the Slot 1 advertiser. `payment` and `winner_payoff` contain Slot 1 expected amounts, and `revenue` is total expected payment per impression. Monetary response fields are decimal strings at two decimal places. The frontend sends `Idempotency-Key` to prevent a repeated submission of the same request from creating duplicate records.

### `POST /api/simulations/run`

Runs and persists aggregate results for repeated auctions. Example:

```json
{
  "n_auctions": 1000,
  "mechanism": "both",
  "click_through_rates": [1.0, 0.7, 0.4],
  "valuation": {"mode": "random", "low": 0, "high": 100},
  "seed": 42,
  "profiles": [
    {"label": "Truthful", "alphas": [1, 1, 1, 1]},
    {"label": "80%", "alphas": [0.8, 0.8, 0.8, 0.8]}
  ]
}
```

The mechanism can be `first_price`, `second_price`, `gsp`, `vcg`, `both` (the two original mechanisms), or `all` (all four). The auction count is 1–10,000 and there can be 1–8 uniquely labeled profiles. `click_through_rates` has the same validation and default as manual runs. A profile defines fixed bidding fractions `α_i`, and each bid is `b_i = round(α_i v_i, 2)`. Fractions range from 0 to 1.5; `α=1` is truthful bidding, less than 1 shades bids, and greater than 1 overbids. These are experimental rules, not a general claim that a fixed fraction is optimal. With overbidding, a first-price winner can pay more than their valuation and have negative payoff.

The valuation mode is `random` or `fixed`. Random values are sampled independently and uniformly between the configured low/high bounds, then rounded to two decimals. If no seed is provided, the backend generates one and returns it with `seed_was_generated: true`; a supplied seed must be an integer from 0 to 2,147,483,647. Fixed mode requires four `fixed_values`; every auction repeats that same scenario and the seed does not affect its outcomes.

For a given simulation, valuations are generated once and reused for every profile and mechanism. This paired design means strategy/mechanism comparisons use the same valuation scenarios. The run uses the vectorized batch engine, with the same A→D tie rule as the exact engine. Single-slot results retain the original one-winner payment and utility calculation. GSP/VCG results rank bidders into configured slots, compute CTR-weighted expected payments and utilities, and report social welfare. Up to eight profiles × four mechanisms are evaluated; only aggregates are saved in SQLite, not individual auction rows.

Each `results` block corresponds to one profile/mechanism pair and contains:

| Output | Meaning / denominator |
| --- | --- |
| `revenue.mean`, `median`, `std`, `min`, `max` | Platform payment distribution; sample standard deviation (`0` when `n=1`). Single-slot units are ₹ per auction; multi-slot units are expected ₹ per impression. |
| `revenue.se` | Sample standard deviation divided by `√n`, an estimate of standard error for mean revenue. |
| `avg_winning_bid` | Mean highest submitted bid per auction (₹). |
| `avg_winning_payment` | Mean total payment per auction/impression; equals mean revenue. |
| `avg_winner_payoff` | Mean top-ranked advertiser payoff; for multi-slot runs this is Slot 1's expected utility. |
| `avg_total_expected_utility` | Sum of all advertisers' utility divided by auction count (₹ per impression for multi-slot runs). |
| `avg_bidder_surplus` | Total utility divided by `4 × auction count` (₹ per advertiser-auction pair). |
| `avg_payoff` for A–D | That advertiser's utility divided by auction count; unallocated auctions count as zero. |
| `win_rate` for A–D | Auctions where advertiser receives a slot / completed auctions. Multi-slot rates can sum above 1. |
| `highest_value_win_rate` | Auctions where the selected winner has a maximum valuation divided by auction count. A tied-highest valuation counts as a highest-value win. |
| `overbid_rate` | Auctions with at least one bid above that advertiser's own valuation divided by auction count. |
| `negative_winner_payoff_rate` | Auctions where the winning advertiser's payoff is below zero divided by auction count. |
| `revenue_histogram` | Counts of simulated auction revenue in shared bin edges. Edges are computed across the result blocks in this run so distributions can be compared. |
| `convergence` | Running average revenue at up to 50 evenly spaced sample-size checkpoints from 1 through `n_auctions`. |

Multi-slot result blocks additionally include `avg_social_welfare` and `avg_expected_payment` (both ₹ per impression), `average_click_through_rate`, `average_payment_per_click`, `avg_expected_utility` (per advertiser), and `slot_win_rate`. Social welfare sums `CTR × true valuation`; expected utility sums `CTR × true valuation − expected payment`. The platform's expected revenue is the sum of advertiser expected payments. First-/second-price runs continue to use the original single-slot interpretations.

The response also returns the used seed, valuation configuration, mechanism list, explanatory notes, and metric definitions. `std` is sample standard deviation (`ddof=1`) and is set to zero for a one-auction run. Fractions/rates are between 0 and 1, not percentages.

The frontend's primary simulation result view highlights the first returned profile/mechanism block, compares mean revenue across all returned blocks, and shows the full per-block results table. The optional analysis view derives payoff, win-rate, revenue-distribution, sensitivity, and convergence chart points from these response blocks and the sweep response. All values in the response are raw rupee values or proportions; presentation layers format them as currency or percentages. No per-auction observations are included in the response or stored in the database.

### `POST /api/simulations/sweep`

Computes sensitivity points over alpha values on one common set of random valuation draws. It accepts auction count, mechanism (`first_price`, `second_price`, `gsp`, `vcg`, `both`, or `all`), click-through rates, valuation bounds, optional seed, mode, deviator, others' alpha, and optional alpha grid. In `all` mode all bidders use each tested alpha; in `deviator` mode only the selected bidder varies alpha and the others hold `others_alpha`. Each point returns mean revenue and mean payoff per advertiser; deviator mode also returns deviator mean expected utility and allocation rate. Multi-slot monetary values are in expected rupees per impression. Result includes seed, CTR settings, and valuation settings. This analysis endpoint is not persisted to history.

### Saved experiments and overview

SQLAlchemy 2.x maps one `experiments` table (`app/models.py`). It stores UUID, creation time, type, mechanism, strategy label, JSON configuration, JSON result, JSON metrics, and optional unique idempotency key. Manual records include all four values/bids and the complete calculated result. Simulation records include requested settings, resolved seed, and aggregate result blocks; per-auction data is not stored. `AUCTIONLAB_DATABASE_URL` chooses the database. Startup uses `Base.metadata.create_all`; SQLite initialization also adds the idempotency-key column/index for the earlier table shape. This small compatibility step is not a versioned migration framework.

| Route | Result |
| --- | --- |
| `GET /api/experiments?experiment_type=manual_auction&sort=desc` | List and count; optional type filter (`manual_auction` or `automatic_simulation`), ascending/descending creation date. |
| `GET /api/experiments/{id}` | Summary plus saved configuration and result. |
| `DELETE /api/experiments/{id}` | Permanently removes one record. |
| `GET /api/experiments/{id}/csv` | UTF-8-with-BOM CSV download. Manual export has one advertiser row with valuation, bid, rank, allocation/winner flag, payment, and payoff; multi-slot records also include slot, CTR, per-click price, and expected per-impression values/payments/utilities. Simulation export has one profile/mechanism aggregate row with settings, seed, CTRs, and metrics. No individual simulation-auction export exists because those observations are not stored. |
| `GET /api/overview` | Actual total, manual and simulation counts plus five most recent saved experiments. |

CSV output is generated with Python's `csv.writer`, so values containing commas, quotes, or newlines are escaped. JSON-valued configuration cells are compact JSON, and text fields beginning with spreadsheet formula characters are prefixed defensively. The export is a UTF-8 CSV with BOM for spreadsheet compatibility.

Only a successful manual auction or completed simulation is saved. Sweeps do not create history records. The client-provided idempotency key is unique across experiments; the same key and same request return the existing result, while a different request with that key is rejected.
