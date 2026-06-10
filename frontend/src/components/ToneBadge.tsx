import type { WindowTone } from "../types/api";

const STYLES: Record<WindowTone, { label: string; bg: string; text: string; testColor: string }> = {
  Strong_Positive: {
    label: "Strong Positive",
    bg: "bg-emerald-100",
    text: "text-emerald-800",
    testColor: "green",
  },
  Authentic: {
    label: "Authentic",
    bg: "bg-emerald-100",
    text: "text-emerald-800",
    testColor: "green",
  },
  Mostly_Authentic: {
    label: "Mostly Authentic",
    bg: "bg-neutral-100",
    text: "text-neutral-700",
    testColor: "gray",
  },
  Mixed_Signals: {
    label: "Mixed Signals",
    bg: "bg-amber-100",
    text: "text-amber-800",
    testColor: "amber",
  },
  Concerning: {
    label: "Concerning",
    bg: "bg-red-100",
    text: "text-red-800",
    testColor: "red",
  },
};

interface ToneBadgeProps {
  tone: WindowTone;
}

export default function ToneBadge({ tone }: ToneBadgeProps) {
  const style = STYLES[tone];
  return (
    <span
      className={`inline-flex items-center rounded-full ${style.bg} ${style.text} px-2.5 py-0.5 text-xs font-medium`}
      data-testid="tone-badge"
      data-color={style.testColor}
    >
      {style.label}
    </span>
  );
}
