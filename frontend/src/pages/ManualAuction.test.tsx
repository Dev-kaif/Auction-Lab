import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import ManualAuction from "./ManualAuction";
import type { AuctionOut } from "../types/auction";

// Deliberately NOT what the inputs imply (A has the top bid in the form): proves the UI shows the backend's answer.
const canned: AuctionOut = {
  mechanism: "second_price", winner: "B", winning_bid: "111.00", runner_up_bid: "77.00", payment: "77.00",
  winner_payoff: "3.00", revenue: "77.00", highest_valuation: "100.00", highest_valued_won: false,
  winner_surplus: "3.00", payoff_sign: "positive", any_overbid: false, tie_for_highest_bid: false,
  tied_bidders: [], tie_break_rule: "Ties go to the lowest index.", ranking: ["B", "A", "C", "D"],
  explanation: "BACKEND-EXPLANATION-TEXT", formulas: { winner: "w", payment: "p", payoff: "u", revenue: "R" },
  advertisers: [
    { advertiser: "A", valuation: "100.00", bid: "100.00", rank: 2, won: false, outcome: "Lost", payment: "0.00", payoff: "0.00", overbid: false },
    { advertiser: "B", valuation: "80.00", bid: "111.00", rank: 1, won: true, outcome: "Won", payment: "77.00", payoff: "3.00", overbid: true },
    { advertiser: "C", valuation: "60.00", bid: "60.00", rank: 3, won: false, outcome: "Lost", payment: "0.00", payoff: "0.00", overbid: false },
    { advertiser: "D", valuation: "40.00", bid: "40.00", rank: 4, won: false, outcome: "Lost", payment: "0.00", payoff: "0.00", overbid: false },
  ],
};

const renderPage = () => render(<MemoryRouter><ManualAuction /></MemoryRouter>);
const okFetch = () => vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => canned });

afterEach(() => vi.unstubAllGlobals());

it("sends the entered values and displays the backend's result", async () => {
  const fetchMock = okFetch(); vi.stubGlobal("fetch", fetchMock);
  renderPage();
  await userEvent.click(screen.getByRole("button", { name: /run auction/i }));

  expect(await screen.findByText("Payoffs and ranking")).toBeInTheDocument();
  await userEvent.click(screen.getByText("Calculation and tie rule"));
  await waitFor(() => expect(screen.getByText("BACKEND-EXPLANATION-TEXT")).toBeInTheDocument());
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/auctions/run");
  expect(JSON.parse(init.body)).toEqual({ mechanism: "second_price", valuations: [100, 80, 60, 40], bids: [100, 80, 60, 40], click_through_rates: [1, 0.7, 0.4] });
  expect(screen.getByRole("status")).toHaveTextContent("B wins with a bid of ₹111.00"); // winner comes from the response
  expect(screen.getByRole("status")).not.toHaveTextContent("A wins");
  expect(screen.getAllByText("₹77.00").length).toBeGreaterThan(0);              // payment from the response
  const bRow = screen.getAllByRole("row").find((r) => r.textContent?.includes("winner"))!;
  expect(bRow.querySelector("th")).toHaveTextContent("B");
  expect(bRow).toHaveTextContent("winner");
  expect(bRow).toHaveTextContent("₹3.00");
  expect(screen.getByText("Payoffs and ranking")).toBeInTheDocument();
});

it("blocks invalid input and never calls the backend", async () => {
  const fetchMock = okFetch(); vi.stubGlobal("fetch", fetchMock);
  renderPage();
  const bidA = screen.getByLabelText(/bid for advertiser A/i);
  await userEvent.clear(bidA); await userEvent.type(bidA, "-5");
  await userEvent.click(screen.getByRole("button", { name: /run auction/i }));
  expect(await screen.findByText(/non-negative number/i)).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
});

it("shows backend errors instead of substituting data", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 422, json: async () => ({ error: { message: "bids[A] must be non-negative" } }) }));
  renderPage();
  await userEvent.click(screen.getByRole("button", { name: /run auction/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent("bids[A] must be non-negative");
  expect(screen.queryByText("Payoffs and ranking")).not.toBeInTheDocument();
});

it("reports an unreachable backend", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network")));
  renderPage();
  await userEvent.click(screen.getByRole("button", { name: /run auction/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/cannot reach/i);
});

it("preset buttons and reset change the bid fields", async () => {
  vi.stubGlobal("fetch", okFetch());
  renderPage();
  await userEvent.click(screen.getByRole("button", { name: /apply to all/i }));
  expect(screen.getByLabelText(/bid for advertiser A/i)).toHaveValue("80");
  expect(screen.getByLabelText(/bid for advertiser B/i)).toHaveValue("64");
  await userEvent.click(screen.getAllByRole("button", { name: /bid truthfully/i })[0]);
  expect(screen.getByLabelText(/bid for advertiser A/i)).toHaveValue("100");
  await userEvent.type(screen.getByLabelText(/valuation for advertiser C/i), "9");
  await userEvent.click(screen.getByRole("button", { name: /reset values/i }));
  expect(screen.getByLabelText(/valuation for advertiser C/i)).toHaveValue("60");
});

it("sends editable CTRs to the backend for GSP and shows the returned allocation", async () => {
  const multiResult: AuctionOut = {
    ...canned, mechanism: "gsp", is_multi_slot: true, click_through_rates: [1, 0.65, 0.4],
    social_welfare: "180.00", revenue: "136.00", explanation: "GSP allocation from backend",
    advertisers: canned.advertisers.map((row, i) => ({
      ...row, won: i < 3, slot: i < 3 ? i + 1 : null,
      click_through_rate: i < 3 ? [1, 0.65, 0.4][i] : 0,
      payment_per_click: ["80.00", "60.00", "40.00", "0.00"][i],
      expected_value: ["100.00", "52.00", "24.00", "0.00"][i],
      expected_payment: ["80.00", "39.00", "16.00", "0.00"][i],
      expected_utility: ["20.00", "13.00", "8.00", "0.00"][i],
    })),
  };
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => multiResult });
  vi.stubGlobal("fetch", fetchMock);
  render(<MemoryRouter><ManualAuction mechanism="gsp" /></MemoryRouter>);
  await userEvent.clear(screen.getByLabelText("Click-through rate for slot 2"));
  await userEvent.type(screen.getByLabelText("Click-through rate for slot 2"), "0.65");
  await userEvent.click(screen.getByRole("button", { name: /run auction/i }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toMatchObject({ mechanism: "gsp", click_through_rates: [1, 0.65, 0.4] });
  expect(await screen.findByText(/A → Slot 1 · B → Slot 2 · C → Slot 3/)).toBeInTheDocument();
  expect(screen.getByText("GSP allocation from backend")).toBeInTheDocument();
});

it("blocks increasing CTR values before a multi-slot request", async () => {
  const fetchMock = okFetch(); vi.stubGlobal("fetch", fetchMock);
  render(<MemoryRouter><ManualAuction mechanism="gsp" /></MemoryRouter>);
  await userEvent.clear(screen.getByLabelText("Click-through rate for slot 1"));
  await userEvent.type(screen.getByLabelText("Click-through rate for slot 1"), "0.6");
  await userEvent.click(screen.getByRole("button", { name: /run auction/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/non-increasing order/i);
  expect(fetchMock).not.toHaveBeenCalled();
});
