# AuctionLab frontend

React + TypeScript user interface for exploring first-price and second-price auctions with four advertisers (A, B, C, D). The browser does not implement its own auction result calculator: manual results and repeated-run metrics are returned by the FastAPI backend. The frontend validates and formats inputs, sends API requests, and presents the returned results.

## Run locally

Requires Node.js 18 or newer. Start the backend in a separate terminal first (instructions in [`../backend/README.md`](../backend/README.md)), then from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` requests to `http://localhost:8000` (`vite.config.ts`). To create a production build, run `npm run build`; to serve that build locally, run `npm run preview`.

Run frontend tests with `npm test` from this directory. Tests use Vitest and React Testing Library in jsdom.

## App structure and request flow

`src/main.tsx` mounts the React app and router. `src/App.tsx` maps the workspace to the root route; `src/pages/Workspace.tsx` owns shared mechanism/mode selection and the experiment-history overlay. Shared API functions and error conversion are in `src/api/client.ts`; TypeScript response/request models are in `src/types/`. Reusable cards, buttons, inputs, and auction result views are in `src/components/`. Simulation form/results are shared through `hooks/SimulationContext.tsx`, and input/analysis transformations live in `src/lib/`.

The general flow is: the user changes page controls → the page validates and builds a typed request → the API client sends JSON to `/api/...` → Vite forwards it to FastAPI → backend engine computes outcomes → the page displays the actual response. A backend validation or application failure becomes a readable error alert; inability to connect reports that the backend should be running on port 8000. Forms show inline validation, a busy/loading label while requests are pending, and an initial empty state before a result exists.

## Main workspace

The app uses one primary workspace instead of page navigation. The header provides the AuctionLab identity and opens a compact history overlay. Shared controls choose first-price or second-price and Manual or Automatic mode. Both mode panels remain mounted while hidden so input, result, and simulation settings survive mode switches.

- **Manual mode**: edit A–D values and bids in aligned advertiser rows on desktop and stacked advertiser panels on narrow screens. Each row labels the bidding strategy implied by its current value/bid pair. Apply truthful bids or a configurable fixed fraction, reset the setup, then run one auction. `POST /api/auctions/run` returns ranking, winner, payment, revenue and payoffs. The result reveals ranking and winner in sequence, respects reduced-motion preferences, and uses stacked advertiser summaries on mobile.
- **Automatic mode**: configure auction count, mechanisms, fixed or random valuations, and strategy profiles in a single workflow. The optional seed is under advanced settings. `POST /api/simulations/run` returns actual aggregate metrics and the resolved settings/seed. Results show the first returned mechanism/profile as the headline example, a primary revenue comparison chart for all returned groups, and a complete responsive results view. Secondary analysis stays collapsed until requested; it calls the simulation and sweep endpoints and compares strategies using a shared random seed.
- **Contextual theory**: the selected mechanism explanation stays below the work area. Actual winner, payment, revenue and payoff calculations appear with manual results; concise notes explain truthful second-price bidding and first-price shading.
- **Experiment history**: the header overlay fetches persisted records, filters by type, sorts by date, opens saved configuration/results, downloads CSV and deletes after confirmation. It calls the existing history API and does not create a local archive.

The only primary application route is `/`; unknown paths also resolve to the workspace. Overview, analysis and game-theory material no longer appear as separate navigation destinations. Analysis functionality is preserved inside the automatic workspace, and persistence/CSV handling remains available in the history overlay.

## Auction calculations shown in the UI

For values `v_i` and submitted bids `b_i`, the backend selects the maximum bid. Equal top bids are awarded by fixed order A→B→C→D. The payment is the winner's own bid in first-price, or the highest bid among the other advertisers in second-price. Every losing bidder pays zero. Payoff is `u_i = v_i - p_i` for the winner and zero otherwise; revenue is the winner's payment. The frontend displays those returned fields and does not recompute the auction.

In the simulation, a profile supplies a fraction `α_i` per advertiser and produces `b_i = round(α_i × v_i, 2)`. Truthful is `α=1`; shading is less than 1; a fraction over 1 is overbidding and may yield a negative first-price winner payoff. Fixed fraction strategies are experimental comparison rules, not universally optimal strategies. The backend reuses one valuation sample across every profile/mechanism pair in each run for fair paired comparisons. The exact single-auction path uses decimal half-up rounding; the vectorized simulation uses NumPy rounding to two decimals (ties to even), so inputs exactly at a half-paise boundary can differ between modes.

## Charts and metric interpretation

The automatic workspace's main revenue chart and expandable analysis section use chart data derived from API responses; `src/lib/analysis.ts` reorganizes result blocks but does not synthesize auction outcomes. The primary chart is mean platform revenue by strategy and mechanism:

1. **Average platform revenue** — average winner payment/revenue (₹ per auction), with standard-error bars, grouped by profile and mechanism. This is the always-visible comparison chart.

The optional analysis section provides supporting views:

2. **Average payoff per advertiser** — each advertiser's payoff averaged over all auctions, with losses contributing zero (₹ per auction). This is not the average winning bidder payoff.
3. **Win rate by advertiser** — wins divided by the number of simulated auctions; proportions sum to 100% across A–D.
4. **Revenue distribution** — count of auctions in each backend-provided shared revenue bin; horizontal ranges are rupees.
5. **Strategy sensitivity** — payoff versus alpha. In deviator mode the selected advertiser varies alpha while the other three use the fixed reference fraction; mechanism curves use the same valuation draws.
6. **Revenue convergence** — running mean revenue at backend-provided sample-size checkpoints; the x-axis is auctions included and y-axis is ₹ per auction.

Mean winner payoff is the winning advertiser's payoff summed across auctions divided by auctions. Average bidder surplus divides total payoff by four advertisers times auction count. The sensitivity view calls out this distinction. Random runs show the resolved seed; fixed valuation runs repeat the same values, so outcomes are deterministic and the seed has no effect. Backend metric definitions and exact numeric values are available in the API response and saved simulation details.

## Saved history and exports

The frontend refreshes history data from the backend database; it does not maintain a browser-side archive. Successful manual and automatic runs are saved by the backend. Analysis sweeps are not saved. History detail shows the original configuration and full stored result JSON, including resolved seed and aggregate simulation metrics. Automatic simulation records contain aggregate metrics only, so their CSV has one row per profile/mechanism result and there is no per-auction detail export. Manual CSV has one row per advertiser. Downloads are linked to `GET /api/experiments/{id}/csv`.

The request client attaches an `Idempotency-Key` to completed manual/simulation requests so browser retries or repeated submissions with the same key and body do not create duplicate records. API response and validation contracts are detailed in [`../backend/README.md`](../backend/README.md).

## UI states and accessibility

Pages provide progress status for in-flight calls, inline field-level validation, alert roles for request errors, and helpful empty states before there is data. The aggregate desktop table is replaced by stacked strategy-result rows on narrow screens; manual results similarly switch from a table to advertiser summaries. History is a responsive experiment list rather than a wide table. Charts use responsive containers with a larger primary comparison chart and supporting plots behind the analysis disclosure. Inputs, mode controls, and run actions expand to comfortable touch targets on mobile.
