import { parseAmount } from "./validation";

describe("parseAmount", () => {
  it.each(["0", "100", "80.5", "0.01", "1000000", " 42 "])("accepts %s", (s) => {
    expect(parseAmount(s).ok).toBe(true);
  });
  it.each(["", "  ", "-1", "abc", "NaN", "Infinity", "1e3", "1,000", "12.345", "1000000.01", "--5", ".5"])("rejects %j", (s) => {
    expect(parseAmount(s).ok).toBe(false);
  });
  it("returns the numeric value", () => {
    expect(parseAmount("80.5")).toEqual({ ok: true, value: 80.5 });
  });
});
