import { memo, useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Formatter } from "recharts/types/component/DefaultTooltipContent";
import type { ChartPoint, LogRecord } from "@/utils/stats";

export type TimeseriesChartProps = {
  data: ChartPoint[];
  color: string;
  label: string;
  valueFormatter?: (value: number) => string;
  tooltipFormatter?: (meta: unknown, value: number) => string;
};

const formatTimestamp = (value: number) => {
  const date = new Date(value);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
};

const defaultValueFormatter = (value: number) => `${value} мс`;

const isLogRecord = (value: unknown): value is LogRecord => {
  return !!value && typeof value === "object" && "traffic_light" in value && "timestamp" in value;
};

const TimeseriesChartComponent = ({
  data,
  color,
  label,
  valueFormatter = defaultValueFormatter,
  tooltipFormatter,
}: TimeseriesChartProps) => {
  const tooltipValueFormatter = useMemo<Formatter<number, string>>(() => {
    return (value, __, item) => {
      const meta = item?.payload?.meta as unknown;
      if (typeof value !== "number" || Number.isNaN(value)) {
        return ["", ""];
      }

      if (tooltipFormatter) {
        return [tooltipFormatter(meta, value), ""];
      }

      if (isLogRecord(meta)) {
        return [
          `${label}: ${valueFormatter(value)}` +
            `\nHTTP: ${meta.http_status ?? "—"}` +
            `\nTraffic: ${meta.traffic_light}` +
            `\nLatency: ${meta.latency_ms ?? "—"} мс` +
            `\nPing: ${meta.ping_ms ?? "—"} мс` +
            `\nSSL: ${meta.ssl_days_left ?? "—"} дн.` +
            `\nRedirects: ${meta.redirects ?? "—"}` +
            `\nDNS: ${meta.dns_resolved ? "ok" : "fail"}`,
          "",
        ];
      }

      return [`${label}: ${valueFormatter(value)}`, ""];
    };
  }, [label, tooltipFormatter, valueFormatter]);

  return (
    <div className="flex h-full flex-col gap-3 rounded-2xl border border-slate-200/60 bg-white/80 p-4 shadow-sm backdrop-blur">
      <h3 className="text-sm font-semibold text-slate-600">{label}</h3>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} syncId="uptime-timeline" margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="timestamp"
              type="number"
              domain={["auto", "auto"]}
              tickFormatter={(value) => new Date(value).toLocaleTimeString()}
              stroke="#94a3b8"
              tick={{ fontSize: 12 }}
            />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} width={70} />
            <Tooltip
              contentStyle={{ backgroundColor: "rgba(15, 23, 42, 0.9)", borderRadius: 12, border: "none" }}
              labelFormatter={formatTimestamp}
              formatter={tooltipValueFormatter}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export const TimeseriesChart = memo(TimeseriesChartComponent);
