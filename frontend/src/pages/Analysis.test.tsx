import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import App from "../App";
import type { SimulationOut, SweepOut } from "../types/simulation";

const run: SimulationOut = { n_auctions: 2, seed: 99, seed_was_generated: false, mechanisms: ["first_price", "second_price"], valuation: { mode: "random", low: 0, high: 100, distribution: "uniform", fixed_values: null }, notes: [], definitions: {}, results: [] };
const sweep: SweepOut = { n_auctions: 2, seed: 99, seed_was_generated: false, mode: "deviator", deviator: "A", others_alpha: 1, valuation: run.valuation, points: { first_price: [{ alpha: 0.5, mean_revenue: 20, mean_payoff_per_advertiser: 2, deviator_mean_payoff: 8, deviator_win_rate: 0.2 }], second_price: [{ alpha: 0.5, mean_revenue: 30, mean_payoff_per_advertiser: 3, deviator_mean_payoff: 9, deviator_win_rate: 0.3 }] } };
const json = (body: unknown) => ({ ok: true, status: 200, json: async () => body });
const showAnalysis = async () => {
  render(<MemoryRouter><App /></MemoryRouter>);
  await userEvent.click(screen.getByRole("button", { name: "Automatic simulation" }));
  await userEvent.click(screen.getByText("Explore additional analysis"));
};
afterEach(() => vi.unstubAllGlobals());

it("runs paired simulation and strategy sweep using the returned seed and renders actual sensitivity data", async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce(json(run)).mockResolvedValueOnce(json(sweep)); vi.stubGlobal("fetch", fetchMock);
  await showAnalysis(); await userEvent.click(screen.getByRole("button", { name: /run analysis/i }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  expect(fetchMock.mock.calls[0][0]).toBe("/api/simulations/run");
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toMatchObject({ mechanism: "all", click_through_rates: [1, 0.7, 0.4], seed: 99, mode: "deviator" });
  expect(screen.getByText(/Advertiser A's mean utility per auction/)).toBeInTheDocument();
});

it("shows backend failures clearly", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ error: { message: "backend unavailable" } }) }));
  await showAnalysis(); await userEvent.click(screen.getByRole("button", { name: /run analysis/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent("backend unavailable");
});
