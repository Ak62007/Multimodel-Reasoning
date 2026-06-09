import type { Significance } from "../types/api";

const styles: Record<Significance, string> = {
  Low: "bg-neutral-100 text-neutral-700",
  Medium: "bg-neutral-200 text-neutral-800",
  High: "bg-neutral-300 text-neutral-900",
};

export function SignificancePill({ value }: { value: Significance }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs ${styles[value]}`}
      data-testid="significance-pill"
    >
      {value}
    </span>
  );
}
