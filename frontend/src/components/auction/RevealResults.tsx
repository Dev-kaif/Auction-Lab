import { motion, useReducedMotion } from "framer-motion";
import { Trophy } from "lucide-react";
import type { AuctionOut } from "../../types/auction";
import { cn, inr } from "../../lib/utils";

export const STAGES = ["idle", "ranking", "ranked", "winner", "price", "done"] as const;
export type Stage = (typeof STAGES)[number];
const at = (stage: Stage, min: Stage) => STAGES.indexOf(stage) >= STAGES.indexOf(min);

export default function RevealResults({ result, stage }: { result: AuctionOut; stage: Stage }) {
  const reduce = useReducedMotion();
  const byAdv = new Map(result.advertisers.map((a) => [a.advertiser, a]));
  const order = at(stage, "ranked") ? result.ranking : result.advertisers.map((a) => a.advertiser);
  const maxBid = Math.max(...result.advertisers.map((a) => Number(a.bid)), 1);
  const winner = byAdv.get(result.winner)!;
  const second = result.mechanism === "second_price";

  return <section aria-label="Auction results" className="min-w-0 overflow-hidden rounded-2xl border border-[#e4e3df] bg-white p-5 shadow-[0_8px_26px_rgba(27,38,63,.045)] sm:p-7">
    <div className="mb-5 flex flex-wrap items-end justify-between gap-2 border-b border-[#eeede9] pb-4">
      <div><p className="text-xs font-semibold uppercase tracking-[.14em] text-teal-700">02 · Auction outcome</p><h2 className="mt-1 text-xl font-semibold tracking-tight text-[#182440]">The result</h2></div>
      {at(stage, "done") && <span className="text-xs text-navy-500">{result.mechanism === "first_price" ? "First-price" : "Second-price"}</span>}
    </div>

    <ol aria-label={at(stage, "ranked") ? "Bids ranked by amount" : "Submitted bids"} className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {order.map((id) => {
        const a = byAdv.get(id)!; const winnerShown = at(stage, "winner") && a.won;
        return <motion.li key={id} layout={!reduce} transition={{ duration: 0.28 }}
          className={cn("min-w-0 rounded-xl border p-4 transition-colors", winnerShown ? "border-emerald-400 bg-emerald-50" : "border-slate-200 bg-[#fdfdfc]")}>
          <div className="flex items-center justify-between gap-2 text-sm"><span className="font-semibold text-[#263550]">{id}{at(stage, "ranked") && <span className="ml-1 font-normal text-slate-500">#{a.rank}</span>}</span><span className="font-medium tabular-nums text-[#182440]">{inr(a.bid)}</span></div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100" aria-hidden><div className={cn("h-full rounded-full", winnerShown ? "bg-teal-600" : "bg-indigo-600")} style={{ width: `${Math.max(0, Number(a.bid) / maxBid * 100)}%` }} /></div>
        </motion.li>;
      })}
    </ol>

    {at(stage, "winner") && <motion.div initial={reduce ? false : { opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} role="status" className="mt-5 flex items-center gap-3 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
      <Trophy className="h-4 w-4 shrink-0" aria-hidden /><span><b>{result.winner}</b> wins with a bid of {inr(result.winning_bid)}.{result.tie_for_highest_bid && <span className="ml-1">{result.tied_bidders.join(", ")} tied; {result.tie_break_rule}</span>}</span>
    </motion.div>}

    {at(stage, "price") && <motion.p initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }} className="mt-4 rounded-xl bg-[#f4f5f8] px-4 py-4 text-sm leading-6 tabular-nums text-[#34415e]">
      {second ? <>Payment = highest losing bid = {inr(result.runner_up_bid)}.</> : <>Payment = winner&apos;s bid = {inr(result.winning_bid)}.</>}{" "}
      Winner payoff = valuation − payment = {inr(winner.valuation)} − {inr(result.payment)} = <b>{inr(result.winner_payoff)}</b>.
    </motion.p>}

    {at(stage, "done") && <>
      <div className="mt-5 grid grid-cols-1 gap-3 border-y border-slate-100 py-4 sm:grid-cols-3">
        <div><div className="text-navy-500">Payment</div><b className="tabular-nums">{inr(result.payment)}</b></div>
        <div><div className="text-navy-500">Platform revenue</div><b className="tabular-nums">{inr(result.revenue)}</b></div>
        <div><div className="text-navy-500">Winner payoff</div><b className={cn("tabular-nums", result.payoff_sign === "negative" ? "text-red-700" : "text-emerald-700")}>{inr(result.winner_payoff)}</b></div>
      </div>
      <div className="mt-4 hidden max-w-full overflow-x-auto sm:block">
        <table className="w-full min-w-[620px] text-sm">
          <caption className="mb-1 text-left font-semibold text-navy-800">Payoffs and ranking</caption>
          <thead className="text-xs uppercase tracking-wide text-slate-500"><tr><th scope="col" className="py-2 text-left">Advertiser</th><th scope="col" className="px-2 text-right">Value</th><th scope="col" className="px-2 text-right">Bid</th><th scope="col" className="px-2 text-right">Rank</th><th scope="col" className="px-2 text-right">Payment</th><th scope="col" className="px-2 text-right">Payoff</th></tr></thead>
          <tbody>{result.advertisers.map((a) => <tr key={a.advertiser} className={cn("border-t border-slate-100", a.won && "bg-emerald-50 font-medium")}><th scope="row" className="py-3 text-left">{a.advertiser}{a.won && <span className="ml-1 text-emerald-700">winner</span>}</th><td className="px-2 text-right tabular-nums">{inr(a.valuation)}</td><td className="px-2 text-right tabular-nums">{inr(a.bid)}{a.overbid && <span className="ml-1 text-xs text-amber-700">overbid</span>}</td><td className="px-2 text-right tabular-nums">{a.rank}</td><td className="px-2 text-right tabular-nums">{inr(a.payment)}</td><td className={cn("px-2 text-right tabular-nums", Number(a.payoff) < 0 && "text-red-700")}>{inr(a.payoff)}</td></tr>)}</tbody>
        </table>
      </div>
      <dl className="mt-4 grid gap-2 sm:hidden">{result.advertisers.map((a) => <div key={a.advertiser} className={cn("grid grid-cols-[auto_1fr] gap-x-3 rounded-xl border p-3", a.won ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-white")}><dt className="row-span-2 flex items-center gap-2 font-semibold text-[#263550]">{a.advertiser}{a.won && <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] text-emerald-800">Winner</span>}</dt><dd className="text-right text-sm tabular-nums text-slate-700">Value {inr(a.valuation)} · Bid {inr(a.bid)} · #{a.rank}</dd><dd className={cn("text-right text-sm tabular-nums", Number(a.payoff) < 0 ? "text-red-700" : "text-slate-600")}>Payment {inr(a.payment)} · Payoff {inr(a.payoff)}</dd></div>)}</dl>
      <details className="mt-2 text-xs">
        <summary className="cursor-pointer text-navy-600">Calculation and tie rule</summary>
        <div className="mt-1 space-y-1 text-navy-600"><p>{result.explanation}</p><p className="font-mono">{result.formulas.winner} · {result.formulas.payment} · {result.formulas.payoff} · {result.formulas.revenue}</p><p>Ties go to the lowest advertiser index (A before B before C before D).</p></div>
      </details>
    </>}
  </section>;
}
