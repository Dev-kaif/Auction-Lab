import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import App from "../App";
import type { AuctionOut } from "../types/auction";

const result: AuctionOut = { mechanism: "second_price", winner: "A", winning_bid: "100.00", runner_up_bid: "80.00", payment: "80.00", winner_payoff: "20.00", revenue: "80.00", highest_valuation: "100.00", highest_valued_won: true, winner_surplus: "20.00", payoff_sign: "positive", any_overbid: false, tie_for_highest_bid: false, tied_bidders: [], tie_break_rule: "A first", ranking: ["A", "B", "C", "D"], explanation: "backend result", formulas: {}, advertisers: ["A", "B", "C", "D"].map((advertiser, i) => ({ advertiser, valuation: `${100 - i * 20}.00`, bid: `${100 - i * 20}.00`, rank: i + 1, won: i === 0, outcome: i === 0 ? "Won" : "Lost", payment: i === 0 ? "80.00" : "0.00", payoff: i === 0 ? "20.00" : "0.00", overbid: false })) };
afterEach(() => vi.unstubAllGlobals());

it("shows the compact workspace and contextual mechanism explanation without standalone page navigation", () => {
  render(<MemoryRouter><App /></MemoryRouter>);
  expect(screen.getByRole("heading", { name: "AuctionLab" })).toBeInTheDocument();
  expect(screen.getByText(/truthful bidding is weakly dominant/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "First-price auction" })).toHaveAttribute("aria-pressed", "false");
  expect(screen.queryByRole("navigation", { name: "Main" })).not.toBeInTheDocument();
});

it("changes the shared mechanism and sends it to the auction endpoint", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => result }); vi.stubGlobal("fetch", fetchMock);
  render(<MemoryRouter><App /></MemoryRouter>);
  await userEvent.click(screen.getByRole("button", { name: "First-price auction" }));
  await userEvent.click(screen.getByRole("button", { name: /run auction/i }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  expect(JSON.parse(fetchMock.mock.calls[0][1].body).mechanism).toBe("first_price");
  expect(await screen.findByText("backend result")).toBeInTheDocument();
});
