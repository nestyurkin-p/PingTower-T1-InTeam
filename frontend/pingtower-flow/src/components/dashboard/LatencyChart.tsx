import type { ChartPoint } from "@/utils/stats";

import { TimeseriesChart, type TimeseriesChartProps } from "./TimeseriesChart";

export type LatencyChartProps = {
  data: ChartPoint[];
  label?: string;
  valueFormatter?: TimeseriesChartProps["valueFormatter"];
  tooltipFormatter?: TimeseriesChartProps["tooltipFormatter"];
};

export function LatencyChart({
  data,
  label = "Латентность",
  valueFormatter,
  tooltipFormatter,
}: LatencyChartProps) {
  return (
    <TimeseriesChart
      data={data}
      color="#0f172a"
      label={label}
      valueFormatter={valueFormatter}
      tooltipFormatter={tooltipFormatter}
    />
  );
}
