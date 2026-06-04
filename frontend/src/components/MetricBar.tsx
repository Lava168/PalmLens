import clsx from "clsx";

type MetricBarProps = {
  label: string;
  value: string;
  tone?: "sage" | "coral" | "pollen";
  percent: number;
};

export function MetricBar({ label, value, tone = "sage", percent }: MetricBarProps) {
  const toneClass = {
    sage: "bg-sage",
    coral: "bg-coral",
    pollen: "bg-pollen"
  }[tone];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-mineral">{label}</span>
        <span className="shrink-0 font-semibold text-ink">{value}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-celadon/80">
        <div
          className={clsx("h-full rounded-full", toneClass)}
          style={{ width: `${Math.max(2, Math.min(100, percent))}%` }}
        />
      </div>
    </div>
  );
}

