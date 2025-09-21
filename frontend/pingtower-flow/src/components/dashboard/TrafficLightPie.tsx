import { Pie, PieChart, ResponsiveContainer, Tooltip, Cell } from "recharts";
import type { TrafficLightAggregate } from "@/utils/stats";

const COLORS = {
  green: "#22c55e",
  orange: "#f97316",
  red: "#ef4444",
};

export type TrafficLightPieProps = {
  data: TrafficLightAggregate;
  title?: string;
};

export function TrafficLightPie({ data, title = "Статусы" }: TrafficLightPieProps) {
  const transformed = (Object.entries(data) as Array<
    [keyof TrafficLightAggregate, number]
  >).map(([key, value]) => ({
    name: key,
    value,
  }));
  const total = transformed.reduce<number>((sum, item) => sum + item.value, 0);

  return (
    <div className="flex h-full flex-col gap-3 rounded-2xl border border-slate-200/60 bg-white/80 p-4 shadow-sm backdrop-blur">
      <h3 className="text-sm font-semibold text-slate-600">{title}</h3>
      <div className="flex h-full flex-1 items-center justify-center">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={transformed}
              dataKey="value"
              nameKey="name"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={4}
              stroke="#ffffff"
              strokeWidth={2}
              isAnimationActive={false}
            >
              {transformed.map((entry) => (
                <Cell key={entry.name} fill={COLORS[entry.name as keyof typeof COLORS]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number, name: string) => {
                const percentage = total === 0 ? 0 : (value / total) * 100;
                return [`${value} • ${percentage.toFixed(1)}%`, name];
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs text-slate-500">
        {transformed.map((entry) => {
          const percentage = total === 0 ? 0 : (entry.value / total) * 100;
          return (
            <div key={entry.name} className="flex items-center gap-2">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: COLORS[entry.name as keyof typeof COLORS] }}
              />
              <span className="capitalize">
                {entry.name}: {percentage.toFixed(1)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
