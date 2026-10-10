import { useState } from "react";
import { Clock3, Sparkles, Waves } from "lucide-react";
import ManualAuction from "./ManualAuction";
import Simulation from "./Simulation";
import Analysis from "./Analysis";
import History from "./History";
import type { Mechanism } from "../types/auction";

type Mode = "manual" | "automatic";
const mechanismOptions: { value: Mechanism; label: string }[] = [
  { value: "first_price", label: "First-price auction" },
  { value: "second_price", label: "Second-price auction" },
];

function Segment<T extends string>({ label, value, options, onChange }: {
  label: string; value: T; options: { value: T; label: string }[]; onChange: (value: T) => void;
}) {
  return <fieldset className="min-w-0">
    <legend className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-navy-500">{label}</legend>
    <div className="flex rounded-xl bg-[#f0f1f5] p-1" role="group" aria-label={label}>
      {options.map((option) => <button key={option.value} type="button" aria-pressed={value === option.value}
        onClick={() => onChange(option.value)}
        className={`min-h-10 flex-1 rounded-lg px-3 text-sm font-medium transition-all duration-150 ${value === option.value ? "bg-white text-[#263879] shadow-sm ring-1 ring-black/5" : "text-slate-600 hover:text-slate-900"}`}>
        {option.label}
      </button>)}
    </div>
  </fieldset>;
}

export default function Workspace() {
  const [mode, setMode] = useState<Mode>("manual");
  const [mechanism, setMechanism] = useState<Mechanism>("second_price");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [analysisOpen, setAnalysisOpen] = useState(false);

  return <main className="min-h-screen bg-[#f6f5f2] text-[#14213d]">
    <header className="border-b border-[#e8e7e2] bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#293b83] text-white shadow-sm"><Waves className="h-5 w-5" aria-hidden /></div>
          <div><h1 className="text-lg font-semibold leading-tight tracking-tight">AuctionLab</h1><p className="mt-0.5 text-xs text-slate-500">Game Theory Simulator</p></div>
        </div>
        <button type="button" onClick={() => setHistoryOpen(true)} className="inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm font-medium text-[#35477f] transition-colors hover:bg-[#f3f4f8] focus-visible:outline-offset-2">
          <Clock3 className="h-4 w-4" aria-hidden /><span className="hidden sm:inline">Experiment history</span><span className="sm:hidden">History</span>
        </button>
      </div>
    </header>

    <div className="mx-auto max-w-6xl space-y-7 px-4 py-6 sm:px-6 sm:py-8">
      <section className="grid gap-5 rounded-2xl border border-[#e8e7e2] bg-white p-4 shadow-[0_3px_14px_rgba(22,34,61,0.035)] sm:grid-cols-2 sm:gap-6 sm:p-5" aria-label="Experiment controls">
        <Segment label="Auction mechanism" value={mechanism} options={mechanismOptions} onChange={setMechanism} />
        <Segment label="Experiment mode" value={mode} options={[{ value: "manual", label: "Manual auction" }, { value: "automatic", label: "Automatic simulation" }]} onChange={setMode} />
      </section>

      <div className="flex items-start gap-3 px-1" aria-live="polite">
        <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-[#5266aa]" aria-hidden />
        <p className="text-sm leading-6 text-slate-600">
          {mechanism === "first_price"
            ? <>First-price: the highest bidder wins and pays <strong className="font-semibold text-slate-800">their own bid</strong>. Bid shading trades off winning probability against payoff.</>
            : <>Second-price: the highest bidder wins and pays the <strong className="font-semibold text-slate-800">second-highest bid</strong>. Under standard independent private values, truthful bidding is weakly dominant.</>}
        </p>
      </div>

      <section hidden={mode !== "manual"} aria-label="Manual auction workspace">
        <ManualAuction mechanism={mechanism} onMechanismChange={setMechanism} compact />
      </section>
      <section hidden={mode !== "automatic"} aria-label="Automatic simulation workspace">
        <Simulation mechanism={mechanism} onMechanismChange={setMechanism} compact />
      </section>

      {mode === "automatic" && <section className="overflow-hidden rounded-2xl border border-[#e5e5e1] bg-white shadow-[0_3px_14px_rgba(22,34,61,0.025)]">
        <button type="button" aria-expanded={analysisOpen} onClick={() => setAnalysisOpen((open) => !open)} className="flex min-h-16 w-full cursor-pointer items-center list-none px-5 py-4 text-left text-sm font-semibold text-[#263879] hover:bg-[#fbfbfa] sm:px-6">
          <span className="inline-flex items-center gap-2"><span className="grid h-7 w-7 place-items-center rounded-lg bg-[#eef0f8] text-[#405399]"><Sparkles className="h-3.5 w-3.5" aria-hidden /></span>Explore additional analysis<span className="ml-auto text-xs font-normal text-slate-500">Payoffs · win rates · distribution · sensitivity · convergence</span></span>
        </button>
        {analysisOpen && <div className="border-t border-[#ecece8] px-4 py-5 sm:px-6"><Analysis embedded /></div>}
      </section>}
    </div>

    {historyOpen && <div className="fixed inset-0 z-40 flex justify-end bg-[#111827]/35 backdrop-blur-[2px]" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setHistoryOpen(false); }}>
      <aside role="dialog" aria-modal="true" aria-label="Experiment history" className="h-full w-full max-w-3xl overflow-y-auto border-l border-slate-200 bg-[#fbfaf8] p-4 shadow-2xl sm:p-7">
        <History onClose={() => setHistoryOpen(false)} />
      </aside>
    </div>}
  </main>;
}
