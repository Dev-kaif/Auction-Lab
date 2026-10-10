import { MAX_AMOUNT, parseAmount } from "./validation";
import type { MechanismChoice, RunSimulationRequest, StrategyProfile } from "../types/simulation";

export const ADVERTISER_IDS = ["A", "B", "C", "D"] as const;
export const MAX_ALPHA = 1.5;
export const N_OPTIONS = [100, 1000, 5000, 10000] as const;
export const MAX_SEED = 2_147_483_647;

export interface SimForm {
  n: number; mechanism: MechanismChoice;
  clickThroughRates: string[];
  valMode: "random" | "fixed"; low: string; high: string; fixed: string[]; seed: string;
  useTruthful: boolean; use80: boolean; use75: boolean;
  useCustom: boolean; customAlpha: string;
  useDeviator: boolean; deviator: (typeof ADVERTISER_IDS)[number]; deviatorAlpha: string;
}

export const defaultForm = (): SimForm => ({
  n: 1000, mechanism: "both", clickThroughRates: ["1", "0.7", "0.4"], valMode: "random", low: "0", high: "100", fixed: ["100", "80", "60", "40"], seed: "",
  useTruthful: true, use80: true, use75: false, useCustom: false, customAlpha: "0.9",
  useDeviator: false, deviator: "A", deviatorAlpha: "0.75",
});

/** Parse an alpha in [0, MAX_ALPHA]. */
export function parseAlpha(raw: string): { ok: true; value: number } | { ok: false; error: string } {
  const t = raw.trim();
  if (!/^\d+(\.\d+)?$/.test(t)) return { ok: false, error: "Enter a number between 0 and 1.5." };
  const v = Number(t);
  if (v > MAX_ALPHA) return { ok: false, error: "Bidding fraction must be at most 1.5." };
  return { ok: true, value: v };
}

export type BuildResult = { ok: true; request: RunSimulationRequest } | { ok: false; errors: Record<string, string> };

export function buildRequest(f: SimForm): BuildResult {
  const errors: Record<string, string> = {};
  const profiles: StrategyProfile[] = [];
  const all = (a: number) => [a, a, a, a];

  if (f.useTruthful) profiles.push({ label: "All truthful (α=1)", alphas: all(1) });
  if (f.use80) profiles.push({ label: "All bid 80% (α=0.8)", alphas: all(0.8) });
  if (f.use75) profiles.push({ label: "All bid 75% (α=0.75)", alphas: all(0.75) });
  if (f.useCustom) {
    const a = parseAlpha(f.customAlpha);
    if (a.ok) profiles.push({ label: `All custom (α=${a.value})`, alphas: all(a.value) }); else errors.customAlpha = a.error;
  }
  if (f.useDeviator) {
    const a = parseAlpha(f.deviatorAlpha);
    if (a.ok) {
      const alphas = ADVERTISER_IDS.map((id) => (id === f.deviator ? a.value : 1));
      profiles.push({ label: `${f.deviator} deviates (α=${a.value}), others truthful`, alphas });
    } else errors.deviatorAlpha = a.error;
  }

  const rates = f.clickThroughRates.map((raw, index) => {
    const value = Number(raw.trim());
    if (!raw.trim() || !Number.isFinite(value) || value < 0 || value > 1) {
      errors[`ctr${index}`] = "Enter a click-through rate from 0 to 1.";
    }
    return value;
  });
  if (rates.length < 1 || rates.length > 4) errors.clickThroughRates = "Choose between one and four slots.";
  if (rates.some((rate, index) => index > 0 && rates[index - 1] < rate)) {
    errors.clickThroughRates = "CTR values must stay the same or decrease down the slots.";
  }
  if (profiles.length === 0 && !errors.customAlpha && !errors.deviatorAlpha) errors.profiles = "Select at least one bidding strategy.";
  if (profiles.length > 8) errors.profiles = "Select at most 8 strategies.";

  let valuation: RunSimulationRequest["valuation"] | null = null;
  if (f.valMode === "random") {
    const lo = parseAmount(f.low), hi = parseAmount(f.high);
    if (!lo.ok) errors.low = lo.error;
    if (!hi.ok) errors.high = hi.error;
    if (lo.ok && hi.ok) {
      if (hi.value <= lo.value) errors.high = "Upper bound must be greater than the lower bound.";
      else valuation = { mode: "random", low: lo.value, high: hi.value };
    }
  } else {
    const vals = f.fixed.map((x) => parseAmount(x));
    vals.forEach((v, i) => { if (!v.ok) errors[`fixed${i}`] = v.error; });
    if (vals.every((v) => v.ok)) valuation = { mode: "fixed", fixed_values: vals.map((v) => (v as { value: number }).value) };
  }

  let seed: number | null = null;
  if (f.seed.trim() !== "") {
    if (!/^\d+$/.test(f.seed.trim()) || Number(f.seed) > MAX_SEED) errors.seed = `Seed must be a whole number from 0 to ${MAX_SEED.toLocaleString("en-IN")}, or blank for a random seed.`;
    else seed = Number(f.seed);
  }
  if (Object.keys(errors).length || !valuation) return { ok: false, errors };
  return { ok: true, request: { n_auctions: f.n, mechanism: f.mechanism, click_through_rates: rates, valuation, seed, profiles } };
}

export { MAX_AMOUNT };
