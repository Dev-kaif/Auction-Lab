import { createContext, useContext, useState, type ReactNode } from "react";
import { defaultForm, type SimForm } from "../lib/simulation";
import type { SimulationOut } from "../types/simulation";

interface Ctx {
  form: SimForm; setForm: (f: SimForm) => void;
  result: SimulationOut | null; setResult: (r: SimulationOut | null) => void;
}
const SimulationContext = createContext<Ctx | null>(null);

/** Keeps the simulation form and last result alive while the user navigates between pages. */
export function SimulationProvider({ children }: { children: ReactNode }) {
  const [form, setForm] = useState<SimForm>(defaultForm());
  const [result, setResult] = useState<SimulationOut | null>(null);
  return <SimulationContext.Provider value={{ form, setForm, result, setResult }}>{children}</SimulationContext.Provider>;
}

export function useSimulation(): Ctx {
  const c = useContext(SimulationContext);
  if (!c) throw new Error("useSimulation must be used inside SimulationProvider");
  return c;
}
