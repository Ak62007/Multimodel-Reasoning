import type { Significance } from "../types/api";

const styles: Record<Significance, string> = {
  Low: "bg-white/[0.04] text-neutral-500",
  Medium: "bg-white/[0.08] text-neutral-300",
  High: "bg-sand/15 text-sand",
};

export function SignificancePill({ value }: { value: Significance }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] ${styles[value]}`}
      data-testid="significance-pill"
    >
      {value}
    </span>
  );
}
