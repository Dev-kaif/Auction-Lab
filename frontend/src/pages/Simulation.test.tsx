import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import App from "../App";
import type { SimulationOut } from "../types/simulation";

const block = (mechanism: "first_price" | "second_price") => ({
  profile_label: "Truthful", alphas: [1, 1, 1, 1], mechanism, n_auctions: 1,
  revenue: { mean: 60, median: 60, std: 0, se: 0, min: 60, max: 60 },
  avg_winning_bid: 60, avg_winning_payment: 60, avg_winner_payoff: 20, avg_bidder_surplus: 5,
  highest_value_win_rate: 1, overbid_rate: 0, negative_winner_payoff_rate: 0,
  win_rate: { A: 1, B: 0, C: 0, D: 0 }, avg_payoff: { A: 20, B: 0, C: 0, D: 0 },
  revenue_histogram: { edges: [0, 100], counts: [1] }, convergence: { n: [1], mean: [60] },
});
const result: SimulationOut = { n_auctions: 1, seed: 42, seed_was_generated: false, mechanisms: ["second_price"], valuation: { mode: "fixed", low: null, high: null, distribution: "fixed", fixed_values: [100, 80, 60, 40] }, notes: [], definitions: {}, results: [block("second_price")] };
const renderApp = () => render(<MemoryRouter><App /></MemoryRouter>);
afterEach(() => vi.unstubAllGlobals());

it("runs an automatic simulation with the shared mechanism and displays actual API metrics", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => result }); vi.stubGlobal("fetch", fetchMock);
  renderApp();
  await userEvent.click(screen.getByRole("button", { name: "Automatic simulation" }));
  await userEvent.click(screen.getByRole("button", { name: /run simulation/i }));
  expect((await screen.findAllByText("₹60.00")).length).toBeGreaterThan(0);
  const body = JSON.parse(fetchMock.mock.calls[0][1].body);
  expect(body).toMatchObject({ mechanism: "second_price", n_auctions: 1000 });
  expect(screen.getByRole("region", { name: "Aggregate results by strategy" })).toBeInTheDocument();
});

it("preserves manual and automatic input state when switching modes", async () => {
  renderApp();
  await userEvent.clear(screen.getByLabelText(/valuation for advertiser A/i));
  await userEvent.type(screen.getByLabelText(/valuation for advertiser A/i), "123");
  await userEvent.click(screen.getByRole("button", { name: "Automatic simulation" }));
  await userEvent.click(screen.getByRole("button", { name: "Manual auction" }));
  expect(screen.getByLabelText(/valuation for advertiser A/i)).toHaveValue("123");
});

it("shows API errors without fabricating results", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 422, json: async () => ({ error: { message: "invalid simulation" } }) }));
  renderApp(); await userEvent.click(screen.getByRole("button", { name: "Automatic simulation" }));
  await userEvent.click(screen.getByRole("button", { name: /run simulation/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent("invalid simulation");
});
