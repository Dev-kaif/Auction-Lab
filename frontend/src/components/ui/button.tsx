import * as React from "react";
import { cn } from "../../lib/utils";

type Variant = "primary" | "outline" | "ghost";
const styles: Record<Variant, string> = {
  primary: "bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-300",
  outline: "border border-slate-300 bg-white text-navy-900 hover:bg-slate-100 disabled:text-slate-400",
  ghost: "text-indigo-700 hover:bg-indigo-50 disabled:text-slate-400",
};

export const Button = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md" }>(
  ({ className, variant = "primary", size = "md", type = "button", ...props }, ref) => (
    <button ref={ref} type={type}
      className={cn("inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors disabled:cursor-not-allowed",
        size === "sm" ? "px-2.5 py-1 text-xs" : "px-4 py-2 text-sm", styles[variant], className)} {...props} />
  ),
);
Button.displayName = "Button";
