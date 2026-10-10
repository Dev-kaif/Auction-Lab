export const MAX_AMOUNT = 1_000_000;

export type Parsed = { ok: true; value: number } | { ok: false; error: string };

/** Validate a user-entered amount: finite, non-negative, at most MAX_AMOUNT, at most 2 decimals. */
export function parseAmount(raw: string): Parsed {
  const text = raw.trim();
  if (text === "") return { ok: false, error: "Enter a number." };
  if (!/^\d+(\.\d+)?$/.test(text)) return { ok: false, error: "Use a non-negative number (digits and an optional decimal point)." };
  if (/\.\d{3,}$/.test(text)) return { ok: false, error: "Use at most 2 decimal places." };
  const value = Number(text);
  if (!Number.isFinite(value)) return { ok: false, error: "Value must be finite." };
  if (value > MAX_AMOUNT) return { ok: false, error: `Maximum allowed is ₹${MAX_AMOUNT.toLocaleString("en-IN")}.` };
  return { ok: true, value };
}
