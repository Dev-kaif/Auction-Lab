import type { AuctionOut, ExperimentDetail, ExperimentList, ExperimentSummary, OverviewStats, RunAuctionRequest } from "../types/auction";
import type { RunSimulationRequest as SimRequest, SimulationOut, SweepRequest, SweepOut } from "../types/simulation";

export class ApiError extends Error {
  constructor(message: string, public status?: number) { super(message); }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  } catch {
    throw new ApiError("Cannot reach the AuctionLab backend. Is it running on port 8000?");
  }
  if (!res.ok) {
    let message = `Request failed (${res.status}).`;
    try { message = (await res.json())?.error?.message ?? message; } catch { /* keep default */ }
    throw new ApiError(message, res.status);
  }
  return res.json() as Promise<T>;
}

export const runAuction = (body: RunAuctionRequest) =>
  request<AuctionOut>("/api/auctions/run", { method: "POST", headers: { "Idempotency-Key": requestKey() }, body: JSON.stringify(body) });

export const runSimulation = (body: SimRequest) =>
  request<SimulationOut>("/api/simulations/run", { method: "POST", headers: { "Idempotency-Key": requestKey() }, body: JSON.stringify(body) });

export const runSweep = (body: SweepRequest) =>
  request<SweepOut>("/api/simulations/sweep", { method: "POST", body: JSON.stringify(body) });

export const getExperiments = (filter?: { type?: ExperimentSummary["experiment_type"]; sort?: "asc" | "desc" }) => {
  const query = new URLSearchParams();
  if (filter?.type) query.set("experiment_type", filter.type);
  query.set("sort", filter?.sort ?? "desc");
  return request<ExperimentList>(`/api/experiments?${query.toString()}`);
};
export const getExperiment = (id: string) => request<ExperimentDetail>(`/api/experiments/${encodeURIComponent(id)}`);
export const deleteExperiment = (id: string) => request<{ deleted: boolean; id: string }>(`/api/experiments/${encodeURIComponent(id)}`, { method: "DELETE" });
export const getOverview = () => request<OverviewStats>("/api/overview");
export const experimentCsvUrl = (id: string) => `/api/experiments/${encodeURIComponent(id)}/csv`;

function requestKey(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
