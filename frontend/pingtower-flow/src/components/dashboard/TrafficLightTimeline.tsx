import { memo, useMemo } from "react";
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TrafficLightTimeseriesPoint } from "@/utils/stats";

export type TrafficLightTimelineProps = {
  data: TrafficLightTimeseriesPoint[];
  title?: string;
};

const COLORS = {
  green: "#22c55e",
  orange: "#f97316",
  red: "#ef4444",
};

const formatTimestamp = (value: number) => {
  const date = new Date(value);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
};

export const TrafficLightTimeline = memo(function TrafficLightTimeline({
  data,
  title = "Распределение статусов",
}: TrafficLightTimelineProps) {
  const chartData = useMemo(() => {
    return data.map((point) => {
      const total = point.total || 1;
      return {
        timestamp: point.timestamp,
        green: Number(((point.green / total) * 100).toFixed(2)),
        orange: Number(((point.orange / total) * 100).toFixed(2)),
        red: Number(((point.red / total) * 100).toFixed(2)),
      };
    });
  }, [data]);

  return (
    <div className="flex h-full flex-col gap-3 rounded-2xl border border-slate-200/60 bg-white/80 p-4 shadow-sm backdrop-blur">
      <h3 className="text-sm font-semibold text-slate-600">{title}</h3>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} syncId="traffic-timeline" margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="timestamp"
              type="number"
              domain={["auto", "auto"]}
              tickFormatter={(value) => new Date(value).toLocaleTimeString()}
              stroke="#94a3b8"
              tick={{ fontSize: 12 }}
            />
            <YAxis
              stroke="#94a3b8"
              tick={{ fontSize: 12 }}
              width={60}
              domain={[0, 100]}
              tickFormatter={(value) => `${value}%`}
            />
            <Tooltip
              contentStyle={{ backgroundColor: "rgba(15, 23, 42, 0.9)", borderRadius: 12, border: "none" }}
              labelFormatter={formatTimestamp}
              formatter={(value: number, name: string) => [`${value.toFixed(1)}%`, name]}
            />
            <Legend formatter={(value) => value.toUpperCase()} iconType="circle" />
            <Area
              type="monotone"
              dataKey="green"
              stackId="traffic"
              stroke={COLORS.green}
              fill={COLORS.green}
              fillOpacity={0.4}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="orange"
              stackId="traffic"
              stroke={COLORS.orange}
              fill={COLORS.orange}
              fillOpacity={0.4}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="red"
              stackId="traffic"
              stroke={COLORS.red}
              fill={COLORS.red}
              fillOpacity={0.4}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
