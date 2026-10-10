import * as React from "react";
import { cn } from "../../lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input ref={ref}
      className={cn("w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm tabular-nums text-navy-900",
        "disabled:bg-slate-100 disabled:text-slate-500 aria-[invalid=true]:border-red-500", className)} {...props} />
  ),
);
Input.displayName = "Input";
