import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import axios, { CanceledError } from "axios";
import clsx from "clsx";
import {
  aggregateTrafficLight,
  buildTimeseries,
  buildTrafficLightTimeseries,
  calcAvgLatency,
  calcAvgPing,
  calcDnsSuccessRate,
  calcUptime,
  countIncidents,
  getSparklineSeries,
  minSslDays,
  type ChartPoint,
  type LogRecord,
  type TrafficLight,
} from "@/utils/stats";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { TrafficLightPie } from "@/components/dashboard/TrafficLightPie";
import { LatencyChart } from "@/components/dashboard/LatencyChart";
import { PingChart } from "@/components/dashboard/PingChart";
import { TimeseriesChart } from "@/components/dashboard/TimeseriesChart";
import { TrafficLightTimeline } from "@/components/dashboard/TrafficLightTimeline";
import {
  LogsTable,
  type LogsTableFilters,
} from "@/components/dashboard/LogsTable";
import { LogDetailsDrawer } from "@/components/dashboard/LogDetailsDrawer";
import { IncidentBanner } from "@/components/dashboard/IncidentBanner";
import { Check, ChevronDown, RefreshCw } from "lucide-react";

const API_URL = "http://localhost:8000";

const TIME_RANGES = [
  { value: "1s", label: "1 сек", durationMs: 1_000 },
  { value: "1m", label: "1 мин", durationMs: 60_000 },
  { value: "10m", label: "10 мин", durationMs: 600_000 },
  { value: "60m", label: "1 час", durationMs: 3_600_000 },
  { value: "1d", label: "1 день", durationMs: 86_400_000 },
  { value: "1w", label: "1 неделя", durationMs: 604_800_000 },
] as const;

const OVERVIEW_LIMIT = 2000;
const DEFAULT_LIMIT = 500;
const TRAFFIC_OPTIONS: TrafficLight[] = ["green", "orange", "red"];

const TRAFFIC_LABELS: Record<TrafficLight, string> = {
  green: "Стабильно",
  orange: "Предупреждения",
  red: "Инциденты",
};

const TRAFFIC_BADGE: Record<TrafficLight, string> = {
  green: "border-emerald-200 bg-emerald-50 text-emerald-600",
  orange: "border-amber-200 bg-amber-50 text-amber-600",
  red: "border-rose-200 bg-rose-50 text-rose-600",
};


const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

const buildTrend = (series: ChartPoint[], limit = 120) => {
  return series.slice(-limit).map((point) => ({ timestamp: point.timestamp, value: point.value }));
};


type Site = {
  name: string;
  url: string;
};

const getInitials = (site: Site) => {
  if (site.name) {
    return site.name
      .split(" ")
      .filter(Boolean)
      .map((part) => part[0]?.toUpperCase())
      .slice(0, 2)
      .join("") || "?";
  }
  try {
    const { hostname } = new URL(site.url);
    return hostname
      .split(".")
      .filter(Boolean)
      .map((part) => part[0]?.toUpperCase())
      .slice(0, 2)
      .join("") || "?";
  } catch {
    return "?";
  }
};

const getHostname = (site: Site) => {
  try {
    return new URL(site.url).hostname;
  } catch {
    return site.url;
  }
};

const formatMs = (value: number | null) => (value === null ? "—" : `${Math.round(value)} мс`);
const formatPercent = (value: number | null, digits = 1) =>
  value === null ? "—" : `${value.toFixed(digits)}%`;
const formatDays = (value: number | null, digits = 1) =>
  value === null ? "—" : `${value.toFixed(digits)} дн.`;

export default function DashboardPage() {
  // --- state (без изменений)
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSiteUrl, setSelectedSiteUrl] = useState<string>("");
  const [timeRange, setTimeRange] = useState<(typeof TIME_RANGES)[number]["value"]>("1m");
  const [logs, setLogs] = useState<LogRecord[]>([]);
  const [overviewLogs, setOverviewLogs] = useState<LogRecord[]>([]);
  const [isOverviewLoading, setIsOverviewLoading] = useState(false);
  const [isSiteLoading, setIsSiteLoading] = useState(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const [autoRefreshInterval, setAutoRefreshInterval] = useState(1);
  const [trafficFilter, setTrafficFilter] = useState<Set<TrafficLight>>(new Set(TRAFFIC_OPTIONS));
  const [httpStatusRange, setHttpStatusRange] = useState({ min: 100, max: 599 });
  const [searchTerm, setSearchTerm] = useState("");
  const [limit, setLimit] = useState(DEFAULT_LIMIT);
  const [selectedLog, setSelectedLog] = useState<LogRecord | null>(null);
  const [sitePickerOpen, setSitePickerOpen] = useState(false);
  const sitePickerRef = useRef<HTMLDivElement | null>(null);
  const timeRangeConfig = useMemo(
    () => TIME_RANGES.find((option) => option.value === timeRange) ?? TIME_RANGES[1],
    [timeRange],
  );

  useEffect(() => {
    let isMounted = true;
    const loadSites = async () => {
      try {
        const response = await axios.get<Site[]>(`${API_URL}/sites`);
        if (!isMounted) return;
        setSites(response.data);
        if (response.data.length > 0) {
          setSelectedSiteUrl((current) => current || response.data[0].url);
        }
      } catch (err) {
        console.error("Failed to load sites", err);
        if (isMounted) {
          setOverviewError("Не удалось загрузить список сайтов");
        }
      }
    };

    loadSites();
    return () => {
      isMounted = false;
    };
  }, []);

  const fetchOverviewData = useCallback(
    async (signal?: AbortSignal) => {
      setIsOverviewLoading(true);
      const since = new Date(Date.now() - timeRangeConfig.durationMs).toISOString();
      try {
        const response = await axios.get<LogRecord[]>(`${API_URL}/logs`, {
          params: {
            since,
            limit: OVERVIEW_LIMIT,
          },
          signal,
        });
        if (signal?.aborted) return;
        const payload = Array.isArray(response.data) ? response.data : [];
        setOverviewLogs(payload);
        setOverviewError(null);
      } catch (err) {
        if (err instanceof CanceledError || signal?.aborted) {
          return;
        }
        console.error("Failed to load overview", err);
        setOverviewError("Не удалось загрузить общую статистику");
      } finally {
        if (!signal?.aborted) {
          setIsOverviewLoading(false);
        }
      }
    },
    [timeRangeConfig.durationMs],
  );

  const fetchSiteData = useCallback(
    async (signal?: AbortSignal) => {
      if (!selectedSiteUrl) {
        setLogs([]);
        setError(null);
        return;
      }

      setIsSiteLoading(true);
      const since = new Date(Date.now() - timeRangeConfig.durationMs).toISOString();

      try {
        const response = await axios.get<LogRecord[]>(`${API_URL}/logs`, {
          params: {
            url: selectedSiteUrl,
            limit,
            since,
          },
          signal,
        });

        if (signal?.aborted) return;

        const payload = Array.isArray(response.data) ? response.data : [];
        setLogs(payload);
        setError(null);
        setLastUpdated(new Date());
      } catch (err) {
        if (err instanceof CanceledError || signal?.aborted) {
          return;
        }
        console.error("Failed to load site dashboard", err);
        setError("Не удалось загрузить данные сайта");
      } finally {
        if (!signal?.aborted) {
          setIsSiteLoading(false);
        }
      }
    },
    [limit, selectedSiteUrl, timeRangeConfig.durationMs],
  );

  useEffect(() => {
    const controller = new AbortController();
    fetchOverviewData(controller.signal);
    return () => controller.abort();
  }, [fetchOverviewData]);

  useEffect(() => {
    const controller = new AbortController();
    fetchSiteData(controller.signal);
    return () => controller.abort();
  }, [fetchSiteData]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!sitePickerRef.current) return;
      if (!sitePickerRef.current.contains(event.target as Node)) {
        setSitePickerOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSitePickerOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  useEffect(() => {
    if (!autoRefreshEnabled) return;
    const intervalId = window.setInterval(() => {
      fetchOverviewData();
      fetchSiteData();
    }, clamp(autoRefreshInterval, 1, 60) * 1000);
    return () => window.clearInterval(intervalId);
  }, [autoRefreshEnabled, autoRefreshInterval, fetchOverviewData, fetchSiteData]);

  const handleManualRefresh = useCallback(() => {
    fetchOverviewData();
    fetchSiteData();
  }, [fetchOverviewData, fetchSiteData]);

  const sortedOverviewLogs = useMemo(
    () =>
      [...overviewLogs].sort(
        (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      ),
    [overviewLogs],
  );

  const sortedLogs = useMemo(
    () => [...logs].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()),
    [logs],
  );

  const filters: LogsTableFilters = useMemo(
    () => ({
      traffic: trafficFilter,
      statusRange: httpStatusRange,
      search: searchTerm,
      limit,
    }),
    [trafficFilter, httpStatusRange, searchTerm, limit],
  );

  const filteredLogs = useMemo(() => {
    return sortedLogs.filter((log) => {
      const trafficAllowed = filters.traffic.size === 0 || filters.traffic.has(log.traffic_light as TrafficLight);
      if (!trafficAllowed) return false;

      const status = log.http_status;
      const statusAllowed =
        status === null || (status >= filters.statusRange.min && status <= filters.statusRange.max);
      if (!statusAllowed) return false;

      if (filters.search.trim().length > 0) {
        const value = log.url ?? "";
        if (!value.toLowerCase().includes(filters.search.toLowerCase())) {
          return false;
        }
      }

      return true;
    });
  }, [filters, sortedLogs]);

  const selectedSite = useMemo(
    () => sites.find((site) => site.url === selectedSiteUrl) ?? null,
    [sites, selectedSiteUrl],
  );

  useEffect(() => {
    setSitePickerOpen(false);
  }, [selectedSiteUrl]);

  const overviewLatencySeries = useMemo(
    () => buildTimeseries(sortedOverviewLogs, "latency_ms"),
    [sortedOverviewLogs],
  );
  const overviewPingSeries = useMemo(
    () => buildTimeseries(sortedOverviewLogs, "ping_ms"),
    [sortedOverviewLogs],
  );
  const overviewDnsSeries = useMemo(
    () => buildTimeseries(sortedOverviewLogs, "dns_success_rate"),
    [sortedOverviewLogs],
  );
  const overviewSslSeries = useMemo(
    () => buildTimeseries(sortedOverviewLogs, "ssl_days_left"),
    [sortedOverviewLogs],
  );
  const overviewTrafficSeries = useMemo(
    () => buildTrafficLightTimeseries(sortedOverviewLogs),
    [sortedOverviewLogs],
  );

  const overviewTraffic = useMemo(
    () => aggregateTrafficLight(sortedOverviewLogs),
    [sortedOverviewLogs],
  );
  const overviewUptime = useMemo(() => calcUptime(sortedOverviewLogs), [sortedOverviewLogs]);

  const overviewUptimeTrend = useMemo<{ timestamp: number; value: number }[]>(() => {
    return overviewTrafficSeries
      .map<{ timestamp: number; value: number } | null>((point) => {
        const { total } = point;
        if (!total) return null;
        return {
          timestamp: point.timestamp,
          value: Number(((point.green / total) * 100).toFixed(1)),
        };
      })
      .filter((value): value is { timestamp: number; value: number } => value !== null);
  }, [overviewTrafficSeries]);

  const overviewLatencyTrend = useMemo(() => buildTrend(overviewLatencySeries), [overviewLatencySeries]);
  const overviewPingTrend = useMemo(() => buildTrend(overviewPingSeries), [overviewPingSeries]);
  const overviewDnsTrend = useMemo(() => buildTrend(overviewDnsSeries), [overviewDnsSeries]);
  const overviewSslTrend = useMemo(() => buildTrend(overviewSslSeries), [overviewSslSeries]);

  const overviewLatencyAvg = useMemo(() => calcAvgLatency(sortedOverviewLogs), [sortedOverviewLogs]);
  const overviewPingAvg = useMemo(() => calcAvgPing(sortedOverviewLogs), [sortedOverviewLogs]);
  const overviewDnsSuccess = useMemo(
    () => calcDnsSuccessRate(sortedOverviewLogs),
    [sortedOverviewLogs],
  );
  const overviewSslDaysLeft = useMemo(() => minSslDays(sortedOverviewLogs), [sortedOverviewLogs]);

  const overviewSummary = useMemo(
    () => ({
      latency_avg: overviewLatencyAvg,
      ping_avg: overviewPingAvg,
      dns_success_rate: overviewDnsSuccess,
      ssl_days_left_avg: overviewSslDaysLeft,
    }),
    [overviewDnsSuccess, overviewLatencyAvg, overviewPingAvg, overviewSslDaysLeft],
  );

  const siteTraffic = useMemo(() => aggregateTrafficLight(sortedLogs), [sortedLogs]);

  const siteLatencySeries = useMemo(() => buildTimeseries(sortedLogs, "latency_ms"), [sortedLogs]);
  const sitePingSeries = useMemo(() => buildTimeseries(sortedLogs, "ping_ms"), [sortedLogs]);
  const siteDnsSeries = useMemo(
    () => buildTimeseries(sortedLogs, "dns_success_rate"),
    [sortedLogs],
  );
  const siteSslSeries = useMemo(
    () => buildTimeseries(sortedLogs, "ssl_days_left"),
    [sortedLogs],
  );

  const siteLatencyTrend = useMemo(() => buildTrend(siteLatencySeries), [siteLatencySeries]);
  const sitePingTrend = useMemo(() => buildTrend(sitePingSeries), [sitePingSeries]);
  const siteDnsTrend = useMemo(() => buildTrend(siteDnsSeries), [siteDnsSeries]);
  const siteSslTrend = useMemo(() => buildTrend(siteSslSeries), [siteSslSeries]);

  const siteLatencyAvg = useMemo(() => calcAvgLatency(sortedLogs), [sortedLogs]);
  const sitePingAvg = useMemo(() => calcAvgPing(sortedLogs), [sortedLogs]);
  const siteDnsSuccess = useMemo(() => calcDnsSuccessRate(sortedLogs), [sortedLogs]);
  const siteSslDaysLeft = useMemo(() => minSslDays(sortedLogs), [sortedLogs]);
  const siteChecks = sortedLogs.length;
  const uptime = useMemo(() => calcUptime(sortedLogs), [sortedLogs]);
  const sslDaysLeftMin = siteSslDaysLeft;
  const incidentsCount = useMemo(() => countIncidents(filteredLogs), [filteredLogs]);

  const latencyDrawerTrend = useMemo(() => {
    if (!selectedLog) return [];
    const index = sortedLogs.findIndex((log) => log.timestamp === selectedLog.timestamp);
    const slice = index === -1 ? sortedLogs.slice(-10) : sortedLogs.slice(Math.max(0, index - 9), index + 1);
    return getSparklineSeries(slice, "latency_ms");
  }, [selectedLog, sortedLogs]);

  const pingDrawerTrend = useMemo(() => {
    if (!selectedLog) return [];
    const index = sortedLogs.findIndex((log) => log.timestamp === selectedLog.timestamp);
    const slice = index === -1 ? sortedLogs.slice(-10) : sortedLogs.slice(Math.max(0, index - 9), index + 1);
    return getSparklineSeries(slice, "ping_ms");
  }, [selectedLog, sortedLogs]);

  const latestLog = filteredLogs[filteredLogs.length - 1] ?? sortedLogs[sortedLogs.length - 1] ?? null;
  const activeTrafficLight = (latestLog?.traffic_light ?? "green") as TrafficLight;
  const activeTrafficLabel = TRAFFIC_LABELS[activeTrafficLight];

  const statusBadgeClass = useMemo(() => TRAFFIC_BADGE[activeTrafficLight], [activeTrafficLight]);
  const handleToggleTraffic = useCallback((traffic: TrafficLight) => {
    setTrafficFilter((prev) => {
      const next = new Set(prev);
      if (next.has(traffic)) {
        next.delete(traffic);
        if (next.size === 0) {
          return new Set(TRAFFIC_OPTIONS);
        }
      } else {
        next.add(traffic);
      }
      return next;
    });
  }, []);

  const handleStatusRangeChange = useCallback((range: { min: number; max: number }) => {
    setHttpStatusRange({
      min: clamp(range.min, 100, 599),
      max: clamp(range.max, 100, 599),
    });
  }, []);

  const overviewSiteCount = sites.length;
  const sslAccent =
    sslDaysLeftMin === null ? "default" : sslDaysLeftMin <= 0 ? "danger" : sslDaysLeftMin < 7 ? "warning" : "default";
  const rangeLabel = timeRangeConfig.label;
  const lastUpdatedLabel = lastUpdated ? lastUpdated.toLocaleTimeString() : null;

  return (
    <div className="flex h-full flex-1 flex-col overflow-hidden bg-slate-100/60">
      <div className="flex-1 overflow-y-auto">
        <main className="mx-auto flex max-w-[1600px] flex-col gap-12 px-6 pb-16 pt-8">
          <section className="relative overflow-hidden rounded-[32px] border border-slate-200/70 bg-slate-900 text-white shadow-[0_45px_120px_-60px_rgba(15,23,42,0.85)]">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.4),transparent_55%),radial-gradient(circle_at_bottom_right,rgba(129,140,248,0.35),transparent_55%)]" />
            <div className="relative z-10 px-8 py-9 sm:px-10">
              <div className="flex flex-wrap items-start justify-between gap-6">
                <div className="space-y-3">
                  <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.3em] text-white/70">
                    <span>Дашборд</span>
                    <span className="h-1 w-1 rounded-full bg-white/40" />
                    <span>Все сайты</span>
                  </span>
                  <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">Мониторинг доступности</h1>
                  <p className="max-w-xl text-sm text-white/70">
                    Сводка по всем ресурсам за период «{rangeLabel}». Метрики обновляются автоматически и помогают быстро перейти от общей картины к деталям.
                  </p>
                </div>
                <div className="flex flex-col items-end gap-3 text-right text-sm text-white/70">
                  <div className="inline-flex items-center gap-2 rounded-2xl border border-white/15 bg-white/10 px-4 py-2 shadow-inner">
                    <span className="text-[13px] uppercase tracking-[0.25em] text-white/60">Сайтов</span>
                    <span className="text-2xl font-semibold text-white">{overviewSiteCount}</span>
                  </div>
                  {overviewError ? (
                    <span className="rounded-xl border border-rose-400/60 bg-rose-500/20 px-3 py-1 text-xs text-rose-100 shadow-sm">
                      {overviewError}
                    </span>
                  ) : null}
                </div>
              </div>
              <div className="mt-8 grid gap-4 xl:grid-cols-6">
                <div className="grid gap-4 sm:grid-cols-2 xl:col-span-4 xl:grid-cols-4">
                  <MetricCard
                    title="Доступность"
                    value={formatPercent(overviewUptime)}
                    trend={overviewUptimeTrend}
                    trendFormatter={(value: number) => `${value.toFixed(1)}%`}
                  />
                  <MetricCard
                    title="Средняя латентность"
                    value={formatMs(overviewSummary.latency_avg)}
                    trend={overviewLatencyTrend}
                  />
                  <MetricCard
                    title="Средний пинг"
                    value={formatMs(overviewSummary.ping_avg)}
                    trend={overviewPingTrend}
                  />
                  <MetricCard
                    title="% успешных DNS"
                    value={formatPercent(overviewSummary.dns_success_rate)}
                    trend={overviewDnsTrend}
                    trendFormatter={(value: number) => `${value.toFixed(1)}%`}
                  />
                  <MetricCard
                    title="Средний срок SSL"
                    value={formatDays(overviewSummary.ssl_days_left_avg)}
                    trend={overviewSslTrend}
                    trendFormatter={(value: number) => `${value.toFixed(1)} дн.`}
                  />
                </div>
                <div className="xl:col-span-2">
                  <TrafficLightPie data={overviewTraffic} title="Светофор (все сайты)" />
                </div>
              </div>
            </div>

          <section className="space-y-5">
            <header className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-400">Глобальные тренды</p>
                <h2 className="text-xl font-semibold text-slate-900">Все сайты</h2>
              </div>
              <p className="text-sm text-slate-500">
                Отображение агрегированных значений по всему парку сайтов.
              </p>
            </header>
            <div className="grid gap-4 xl:grid-cols-2">
              <LatencyChart
                data={overviewLatencySeries}
                label="Латентность (все сайты)"
              />
              <PingChart
                data={overviewPingSeries}
                label="Пинг (все сайты)"
              />
            </div>
            <TrafficLightTimeline data={overviewTrafficSeries} title="Распределение статусов (все сайты)" />
          </section>

          </section>
          <div className="relative z-30">
            <div className="rounded-[28px] border border-slate-200 bg-white/95 px-6 py-5 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.5)] backdrop-blur">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div className="flex-1">
                  <div ref={sitePickerRef} className="relative">
                    <button
                      type="button"
                      onClick={() => setSitePickerOpen((prev) => !prev)}
                      className={clsx(
                        "flex w-full items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 text-left text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-200",
                        sitePickerOpen ? "ring-2 ring-sky-200" : undefined,
                      )}
                      aria-haspopup="listbox"
                      aria-expanded={sitePickerOpen}
                    >
                      {selectedSite ? (
                        <div className="flex items-center gap-3">
                          <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-slate-900/5 text-sm font-semibold text-slate-700">
                            {getInitials(selectedSite)}
                          </span>
                          <div className="flex flex-col">
                            <span className="text-sm font-semibold leading-5 text-slate-900">{getHostname(selectedSite)}</span>
                            <span className="text-xs text-slate-400">{selectedSite.url}</span>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center gap-3 text-sm text-slate-400">
                          <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-slate-100 text-sm font-semibold text-slate-400">
                            —
                          </span>
                          <span>Выберите сайт</span>
                        </div>
                      )}
                      <ChevronDown className={clsx("h-4 w-4 text-slate-400 transition", sitePickerOpen ? "rotate-180" : undefined)} />
                    </button>
                    {sitePickerOpen ? (
                      <div className="absolute left-0 right-0 z-30 mt-3 max-h-80 overflow-y-auto rounded-2xl border border-slate-200 bg-white/95 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.45)] backdrop-blur">
                        <ul role="listbox" className="divide-y divide-slate-100/70">
                          {sites.length > 0 ? (
                            sites.map((site) => {
                              const isActive = site.url === selectedSiteUrl;
                              return (
                                <li key={site.url}>
                                  <button
                                    type="button"
                                    role="option"
                                    aria-selected={isActive}
                                    onClick={() => {
                                      setSelectedSiteUrl(site.url);
                                      setSitePickerOpen(false);
                                    }}
                                    className={clsx(
                                      "flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-slate-50",
                                      isActive ? "bg-slate-100/80" : "bg-white/95",
                                    )}
                                  >
                                    <div className="flex items-center gap-3">
                                      <span
                                        className={clsx(
                                          "flex h-9 w-9 items-center justify-center rounded-2xl text-sm font-semibold",
                                          isActive ? "bg-slate-900 text-white" : "bg-slate-900/5 text-slate-700",
                                        )}
                                      >
                                        {getInitials(site)}
                                      </span>
                                      <div className="flex flex-col">
                                        <span className="text-sm font-semibold leading-5 text-slate-900">{getHostname(site)}</span>
                                        <span className="text-xs text-slate-400">{site.url}</span>
                                      </div>
                                    </div>
                                    {isActive ? (
                                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-slate-900 text-white">
                                        <Check className="h-4 w-4" />
                                      </span>
                                    ) : (
                                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 text-slate-300">
                                        <Check className="h-4 w-4 opacity-0" />
                                      </span>
                                    )}
                                  </button>
                                </li>
                              );
                            })
                          ) : (
                            <li className="px-4 py-3 text-sm text-slate-400">Нет доступных сайтов</li>
                          )}
                        </ul>
                      </div>
                    ) : null}
                  </div>
                </div>
                <div className="flex flex-col gap-3 text-sm text-slate-600">
                  <div className="flex flex-wrap items-center justify-end gap-3">
                    <div className="flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-1 py-1 shadow-inner">
                      {TIME_RANGES.map((option) => {
                        const isActive = option.value === timeRange;
                        return (
                          <button
                            key={option.value}
                            type="button"
                            onClick={() => setTimeRange(option.value)}
                            className={clsx(
                              "rounded-full px-3 py-1.5 text-sm font-medium transition",
                              isActive
                                ? "bg-white text-slate-900 shadow"
                                : "text-slate-500 hover:text-slate-700",
                            )}
                          >
                            {option.label}
                          </button>
                        );
                      })}
                    </div>
                    <div className="flex items-center gap-3 rounded-full border border-slate-200 bg-white px-4 py-1.5 text-sm shadow-sm">
                      <span className="text-xs uppercase tracking-wide text-slate-400">Авто</span>
                      <button
                        type="button"
                        aria-pressed={autoRefreshEnabled}
                        onClick={() => setAutoRefreshEnabled((prev) => !prev)}
                        className={clsx(
                          "relative h-6 w-11 rounded-full border transition-colors",
                          autoRefreshEnabled
                            ? "border-slate-900 bg-slate-900"
                            : "border-slate-200 bg-white",
                        )}
                        aria-label="Переключить автообновление"
                      >
                        <span
                          className={clsx(
                            "absolute top-0.5 left-0.5 inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform",
                            autoRefreshEnabled ? "translate-x-5" : "translate-x-0",
                            "transform",
                          )}
                        />
                      </button>
                      <div className="flex items-center gap-1 text-xs text-slate-400">
                        <span>каждые</span>
                        <input
                          type="number"
                          min={1}
                          max={60}
                          step={1}
                          value={autoRefreshInterval}
                          onChange={(event) => setAutoRefreshInterval(clamp(Number(event.target.value) || 1, 1, 60))}
                          className="h-7 w-16 rounded-full border border-slate-200 bg-white px-2 text-right text-sm text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-200"
                          aria-label="Интервал автообновления, секунд"
                        />
                        <span>с</span>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={handleManualRefresh}
                      className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                    >
                      <RefreshCw className={clsx("h-4 w-4", isSiteLoading || isOverviewLoading ? "animate-spin" : undefined)} />
                      Обновить
                    </button>
                  </div>
                  <div className="flex flex-wrap justify-end gap-x-4 gap-y-1 text-xs text-slate-400">
                    {lastUpdatedLabel ? <span>Обновлено {lastUpdatedLabel}</span> : null}
                    {isSiteLoading || isOverviewLoading ? <span>Обновляем данные…</span> : null}
                  </div>
                </div>
              </div>
            </div>
          </div>

          
          <section className="space-y-8 rounded-[28px] border border-slate-200 bg-white/90 px-6 py-7 shadow-sm backdrop-blur">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-400">Выбранный сайт</span>
                <h2 className="text-xl font-semibold text-slate-900">
                  {selectedSite ? getHostname(selectedSite) : "Выберите ресурс"}
                </h2>
                <p className="text-sm text-slate-500">
                  {selectedSite ? selectedSite.url : "Выберите сайт из панели выше, чтобы увидеть детали."}
                </p>
              </div>
              {selectedSite ? (
                <div className="flex flex-col items-end gap-2 text-right">
                  <span className={clsx("inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium", statusBadgeClass)}>
                    <span className="h-2.5 w-2.5 rounded-full bg-current" />
                    {activeTrafficLabel}
                  </span>
                  <span className="text-xs text-slate-400">Последний статус: {activeTrafficLabel.toLowerCase()}</span>
                </div>
              ) : null}
            </div>
            {error ? (
              <div className="rounded-2xl border border-rose-200/80 bg-rose-50/80 px-4 py-3 text-sm text-rose-700 shadow-sm">{error}</div>
            ) : null}
            <div className="grid gap-4 xl:grid-cols-5">
              <div className="grid gap-4 sm:grid-cols-2 xl:col-span-4 xl:grid-cols-4">
                <MetricCard
                  title="Средняя латентность"
                  value={formatMs(siteLatencyAvg)}
                  trend={siteLatencyTrend}
                />
                <MetricCard
                  title="Средний пинг"
                  value={formatMs(sitePingAvg)}
                  trend={sitePingTrend}
                />
                <MetricCard title="Доступность" value={uptime === null ? "—" : `${uptime}%`} />
                <MetricCard
                  title="% успешных DNS"
                  value={formatPercent(siteDnsSuccess)}
                  trend={siteDnsTrend}
                  trendFormatter={(value: number) => `${value.toFixed(1)}%`}
                />
                <MetricCard
                  title="Средний срок SSL"
                  value={formatDays(siteSslDaysLeft)}
                  trend={siteSslTrend}
                  trendFormatter={(value: number) => `${value.toFixed(1)} дн.`}
                  accent={sslAccent}
                />
              </div>
              <MetricCard title="Проверок" value={siteChecks} description="Количество записей в выборке" compact />
            </div>
            <IncidentBanner incidentCount={incidentsCount} windowSize={filteredLogs.length || siteChecks} />
            <div className="grid gap-4 xl:grid-cols-2">
              <LatencyChart
                data={siteLatencySeries}
                label="Латентность сайта"
              />
              <PingChart
                data={sitePingSeries}
                label="Пинг сайта"
              />
            </div>
            <div className="grid gap-4 xl:grid-cols-4">
              <div className="xl:col-span-2">
                <TimeseriesChart
                  data={siteSslSeries}
                  color="#0ea5e9"
                  label="SSL, дни"
                  valueFormatter={(value: number) => `${value.toFixed(1)} дн.`}
                />
              </div>
              <TimeseriesChart
                data={siteDnsSeries}
                color="#22c55e"
                label="DNS, %"
                valueFormatter={(value: number) => `${value.toFixed(1)}%`}
              />
              <TrafficLightPie data={siteTraffic} title="Светофор сайта" />
            </div>
            <LogsTable
              logs={filteredLogs}
              onRowClick={setSelectedLog}
              filters={filters}
              onToggleTraffic={handleToggleTraffic}
              onStatusChange={handleStatusRangeChange}
              onSearchChange={setSearchTerm}
              onLimitChange={setLimit}
            />
          </section>
        </main>
      </div>
      <LogDetailsDrawer
        log={selectedLog}
        open={Boolean(selectedLog)}
        onClose={() => setSelectedLog(null)}
        latencyTrend={latencyDrawerTrend}
        pingTrend={pingDrawerTrend}
      />
    </div>
  );

}

