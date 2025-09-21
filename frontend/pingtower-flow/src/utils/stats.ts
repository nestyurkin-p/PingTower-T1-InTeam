export type TrafficLight = "green" | "orange" | "red";

export type LogRecord = {
  timestamp: string;
  traffic_light: TrafficLight;
  http_status: number | null;
  latency_ms: number | null;
  ping_ms: number | null;
  ssl_days_left: number | null;
  dns_resolved: number | boolean | null;
  redirects: number | null;
  url?: string | null;
};

export type TrafficLightAggregate = {
  green: number;
  orange: number;
  red: number;
};


const asNumber = (value: number | null | undefined) =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

const toFixedNumber = (value: number, digits = 2) => Number(value.toFixed(digits));

export function calcAvgLatency(logs: LogRecord[]): number | null {
  const values = logs
    .map((log) => asNumber(log.latency_ms))
    .filter((value): value is number => value !== null);

  if (values.length === 0) return null;

  const sum = values.reduce((acc, value) => acc + value, 0);
  return Math.round(sum / values.length);
}

export function calcAvgPing(logs: LogRecord[]): number | null {
  const values = logs
    .map((log) => asNumber(log.ping_ms))
    .filter((value): value is number => value !== null);

  if (values.length === 0) return null;

  const sum = values.reduce((acc, value) => acc + value, 0);
  return Math.round(sum / values.length);
}

export function calcUptime(logs: LogRecord[]): number | null {
  if (logs.length === 0) return null;

  const counts = aggregateTrafficLight(logs);
  const total = counts.green + counts.orange + counts.red;
  if (total === 0) return null;

  return Math.round((counts.green / total) * 100);
}

export function minSslDays(logs: LogRecord[]): number | null {
  const values = logs
    .map((log) => asNumber(log.ssl_days_left))
    .filter((value): value is number => value !== null);

  if (values.length === 0) return null;

  return Math.min(...values);
}

export function calcDnsSuccessRate(logs: LogRecord[]): number | null {
  if (logs.length === 0) return null;

  const success = logs.filter((log) => {
    if (log.dns_resolved === null || log.dns_resolved === undefined) return false;
    if (typeof log.dns_resolved === "boolean") return log.dns_resolved;
    return Number(log.dns_resolved) === 1;
  }).length;

  return toFixedNumber((success / logs.length) * 100, 1);
}

export function aggregateTrafficLight(logs: LogRecord[]): TrafficLightAggregate {
  return logs.reduce<TrafficLightAggregate>(
    (acc, log) => {
      acc[log.traffic_light] += 1;
      return acc;
    },
    { green: 0, orange: 0, red: 0 },
  );
}
export function countIncidents(logs: LogRecord[]): number {
  return logs.filter(
    (log) => log.traffic_light === "orange" || log.traffic_light === "red"
  ).length;
}


export function getSparklineSeries(
  logs: LogRecord[],
  field: "latency_ms" | "ping_ms",
): { timestamp: number; value: number }[] {
  return logs
    .map((log) => {
      const value = asNumber(log[field]);
      if (value === null) return null;
      return {
        timestamp: new Date(log.timestamp).getTime(),
        value,
      };
    })
    .filter((value): value is { timestamp: number; value: number } => value !== null);
}

export type ChartPoint<TMeta = unknown> = {
  timestamp: number;
  value: number;
  meta?: TMeta;
};

type TimeseriesField = "latency_ms" | "ping_ms" | "ssl_days_left" | "dns_success_rate";

const resolveTimeseriesValue = (log: LogRecord, field: TimeseriesField): number | null => {
  switch (field) {
    case "latency_ms":
    case "ping_ms":
      return asNumber(log[field]);
    case "ssl_days_left":
      return asNumber(log.ssl_days_left);
    case "dns_success_rate":
      if (log.dns_resolved === null || log.dns_resolved === undefined) return null;
      if (typeof log.dns_resolved === "boolean") {
        return log.dns_resolved ? 100 : 0;
      }
      return Number(log.dns_resolved) === 1 ? 100 : 0;
    default:
      return null;
  }
};

const formatTimeseriesValue = (field: TimeseriesField, value: number) => {
  switch (field) {
    case "dns_success_rate":
      return toFixedNumber(value, 1);
    case "ssl_days_left":
      return toFixedNumber(value, 1);
    default:
      return Math.round(value);
  }
};

export function buildTimeseries(
  logs: LogRecord[],
  field: TimeseriesField,

  maxPoints = 10000,
): ChartPoint<LogRecord>[] {
  const points: ChartPoint<LogRecord>[] = [];

  const safeLogs = logs.filter((log) => resolveTimeseriesValue(log, field) !== null);

  if (safeLogs.length === 0) return points;

  const bucketSize = Math.max(1, Math.ceil(safeLogs.length / maxPoints));

  for (let i = 0; i < safeLogs.length; i += bucketSize) {
    const bucket = safeLogs.slice(i, i + bucketSize);
    const avgValue =

      bucket.reduce((sum, log) => sum + (resolveTimeseriesValue(log, field) ?? 0), 0) /

      bucket.length;
    const referenceLog = bucket[bucket.length - 1];
    points.push({
      timestamp: new Date(referenceLog.timestamp).getTime(),
      value: formatTimeseriesValue(field, avgValue),

      meta: referenceLog,
    });
  }

  return points;
}

export type TrafficLightTimeseriesPoint = {
  timestamp: number;
  green: number;
  orange: number;
  red: number;
  total: number;
};

export function buildTrafficLightTimeseries(
  logs: LogRecord[],
  maxPoints = 1000,
): TrafficLightTimeseriesPoint[] {
  if (logs.length === 0) return [];

  const sortedLogs = [...logs].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );

  const bucketSize = Math.max(1, Math.ceil(sortedLogs.length / maxPoints));
  const points: TrafficLightTimeseriesPoint[] = [];

  for (let i = 0; i < sortedLogs.length; i += bucketSize) {
    const bucket = sortedLogs.slice(i, i + bucketSize);
    const counts = aggregateTrafficLight(bucket);
    const referenceLog = bucket[bucket.length - 1];
    const total = counts.green + counts.orange + counts.red;

    points.push({
      timestamp: new Date(referenceLog.timestamp).getTime(),
      green: counts.green,
      orange: counts.orange,
      red: counts.red,
      total,
    });
  }

  return points;
}

