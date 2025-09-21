import type { ReactNode } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export type MetricCardProps = {
  title: string;
  value: ReactNode;
  description?: string;
  trend?: { timestamp: number; value: number }[];
  accent?: "default" | "warning" | "danger";
  compact?: boolean;
  trendFormatter?: (value: number) => string;
};

const ACCENTS: Record<NonNullable<MetricCardProps["accent"]>, string> = {
  default: "border-slate-200/60 bg-white/80",
  warning: "border-amber-300/70 bg-amber-50/70",
  danger: "border-rose-300/70 bg-rose-50/70",
};

export function MetricCard({
  title,
  value,
  description,
  trend,
  accent = "default",
  compact = false,
  trendFormatter,
}: MetricCardProps) {
  return (
    <Card
      className={`flex h-full flex-col justify-between border ${ACCENTS[accent]} backdrop-blur-sm shadow-none`}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-slate-600">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-3xl font-semibold text-slate-900">{value}</div>
        {description ? (
          <p className="text-xs text-slate-500">{description}</p>
        ) : null}
        {trend && trend.length > 1 ? (
          <div className={`h-14 w-full ${compact ? "mt-1" : "mt-2"}`}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 4, left: 0, right: 0, bottom: 0 }}>
                <XAxis dataKey="timestamp" hide type="number" domain={['auto', 'auto']} />
                <Tooltip
                  wrapperClassName="!bg-slate-900/90 !text-white"
                  labelFormatter={(value) => new Date(value).toLocaleTimeString()}
                  formatter={(value: number) => [trendFormatter ? trendFormatter(value) : `${value.toFixed(0)} мс`, ""]}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#1d4ed8"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
