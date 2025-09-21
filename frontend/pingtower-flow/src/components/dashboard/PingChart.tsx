import type { ChartPoint } from "@/utils/stats";
import { TimeseriesChart, type TimeseriesChartProps } from "./TimeseriesChart";

export type PingChartProps = {
  data: ChartPoint[];
  label?: string;
  valueFormatter?: TimeseriesChartProps["valueFormatter"];
  tooltipFormatter?: TimeseriesChartProps["tooltipFormatter"];
};

export function PingChart({
  data,
  label = "Пинг",
  valueFormatter,
  tooltipFormatter,
}: PingChartProps) {
  return (
    <TimeseriesChart
      data={data}
      color="#2563eb"
      label={label}
      valueFormatter={valueFormatter}
      tooltipFormatter={tooltipFormatter}
    />
  );
}
