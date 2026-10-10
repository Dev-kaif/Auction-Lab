import { buildRequest, defaultForm, parseAlpha, type SimForm } from "./simulation";

const form = (over: Partial<SimForm> = {}): SimForm => ({ ...defaultForm(), ...over });

describe("parseAlpha", () => {
  it.each(["0", "0.8", "1", "1.5"])("accepts %s", (s) => expect(parseAlpha(s).ok).toBe(true));
  it.each(["", "-0.1", "1.51", "abc", "1e0", "NaN"])("rejects %j", (s) => expect(parseAlpha(s).ok).toBe(false));
});

describe("buildRequest", () => {
  it("builds the default request", () => {
    const r = buildRequest(form());
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.request.n_auctions).toBe(1000);
      expect(r.request.mechanism).toBe("both");
      expect(r.request.seed).toBeNull();
      expect(r.request.valuation).toEqual({ mode: "random", low: 0, high: 100 });
      expect(r.request.profiles.map((p) => p.alphas)).toEqual([[1, 1, 1, 1], [0.8, 0.8, 0.8, 0.8]]);
    }
  });
  it("builds a deviator profile with the right advertiser", () => {
    const r = buildRequest(form({ useTruthful: false, use80: false, useDeviator: true, deviator: "C", deviatorAlpha: "0.75" }));
    expect(r.ok && r.request.profiles[0].alphas).toEqual([1, 1, 0.75, 1]);
  });
  it("requires at least one strategy", () => {
    const r = buildRequest(form({ useTruthful: false, use80: false }));
    expect(!r.ok && r.errors.profiles).toBeTruthy();
  });
  it("rejects bad custom alpha and keeps other profiles out of the request", () => {
    const r = buildRequest(form({ useCustom: true, customAlpha: "1.6" }));
    expect(!r.ok && r.errors.customAlpha).toMatch(/1\.5/);
  });
  it("validates random bounds", () => {
    expect(buildRequest(form({ low: "50", high: "50" })).ok).toBe(false);
    expect(buildRequest(form({ low: "-1" })).ok).toBe(false);
    expect(buildRequest(form({ high: "2000000" })).ok).toBe(false);
  });
  it("validates fixed valuations", () => {
    const ok = buildRequest(form({ valMode: "fixed" }));
    expect(ok.ok && ok.request.valuation).toEqual({ mode: "fixed", fixed_values: [100, 80, 60, 40] });
    const bad = buildRequest(form({ valMode: "fixed", fixed: ["100", "x", "60", "40"] }));
    expect(!bad.ok && bad.errors.fixed1).toBeTruthy();
  });
  it("validates the seed", () => {
    expect(buildRequest(form({ seed: "42" })).ok).toBe(true);
    for (const s of ["-1", "1.5", "abc", "2147483648"]) expect(buildRequest(form({ seed: s })).ok).toBe(false);
  });
});
