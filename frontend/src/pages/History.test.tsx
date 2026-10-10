import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import App from "../App";
import type { ExperimentDetail, ExperimentList } from "../types/auction";

const item = { id: "exp-manual-1", created_at: "2026-01-02T03:04:05+00:00", experiment_type: "manual_auction" as const,
  mechanism: "first_price", strategy: "Submitted bids", metrics: { winner: "A", revenue: "90.00", winner_payoff: "10.00" } };
const list: ExperimentList = { items: [item], total: 1 };
const detail: ExperimentDetail = { ...item, configuration: { bids: [90, 72, 45, 28] }, result: { winner: "A", payment: "90.00" } };
const empty: ExperimentList = { items: [], total: 0 };
const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body });
const renderApp = () => render(<MemoryRouter><App /></MemoryRouter>);
const goHistory = async () => userEvent.click(screen.getByRole("button", { name: /experiment history/i }));
afterEach(() => vi.unstubAllGlobals());

it("opens persisted experiment history in a compact overlay", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ok(list)));
  renderApp(); await goHistory();
  expect(await screen.findByText("Submitted bids")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
  expect(screen.queryByRole("navigation", { name: "Main" })).not.toBeInTheDocument();
});

it("filters history by type and shows database-backed experiment details and CSV action", async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce(ok(list)).mockResolvedValueOnce(ok(list)).mockResolvedValueOnce(ok(list)).mockResolvedValueOnce(ok(detail)); vi.stubGlobal("fetch", fetchMock);
  renderApp(); await goHistory();
  expect(await screen.findByText("Submitted bids")).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText("Filter experiment type"), "manual_auction");
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  expect(fetchMock.mock.calls[1][0]).toContain("experiment_type=manual_auction");
  await userEvent.selectOptions(screen.getByLabelText("Sort by date"), "asc");
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
  expect(fetchMock.mock.calls[2][0]).toContain("sort=asc");
  await userEvent.click(screen.getByRole("button", { name: /view details/i }));
  expect(await screen.findByText(/\"bids\": \[/)).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: /download csv/i }).length).toBeGreaterThan(0);
});

it("requires confirmation before deleting and reloads history after deletion", async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce(ok(list)).mockResolvedValueOnce(ok({ deleted: true, id: item.id }))
    .mockResolvedValueOnce(ok(empty)); vi.stubGlobal("fetch", fetchMock);
  renderApp(); await goHistory(); await screen.findByText("Submitted bids");
  await userEvent.click(screen.getByRole("button", { name: /delete exp-manual-1/i }));
  expect(screen.getByRole("alertdialog")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Cancel" }));
  expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /delete exp-manual-1/i }));
  await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Delete experiment" }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
  expect(fetchMock.mock.calls[1][0]).toBe("/api/experiments/exp-manual-1");
  expect(fetchMock.mock.calls[1][1].method).toBe("DELETE");
  expect(await screen.findByText(/No saved experiments match/)).toBeInTheDocument();
});
