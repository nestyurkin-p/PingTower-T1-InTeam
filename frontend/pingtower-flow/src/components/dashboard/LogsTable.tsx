import {
  memo,
  useCallback,
  useMemo,
  useState,
  type CSSProperties,
  type ReactNode,
  type UIEvent,
} from "react";
import type { LogRecord, TrafficLight } from "@/utils/stats";

export type LogsTableFilters = {
  traffic: Set<TrafficLight>;
  statusRange: { min: number; max: number };
  search: string;
  limit: number;
};

export type LogsTableProps = {
  logs: LogRecord[];
  onRowClick: (log: LogRecord) => void;
  filters: LogsTableFilters;
  onToggleTraffic: (traffic: TrafficLight) => void;
  onStatusChange: (range: { min: number; max: number }) => void;
  onSearchChange: (value: string) => void;
  onLimitChange: (value: number) => void;
};

const TRAFFIC_ORDER: TrafficLight[] = ["green", "orange", "red"];
const TRAFFIC_LABELS: Record<TrafficLight, string> = {
  green: "зелёный",
  orange: "оранжевый",
  red: "красный",
};

const TRAFFIC_COLOR: Record<TrafficLight, string> = {
  green: "bg-emerald-400",
  orange: "bg-amber-400",
  red: "bg-rose-400",
};

const LIMIT_OPTIONS = [100, 500, 1000];

const GRID_TEMPLATE =
  "minmax(200px, 1.4fr) minmax(120px, 0.8fr) minmax(80px, 0.6fr) repeat(2, minmax(90px, 0.7fr)) minmax(110px, 0.8fr) minmax(90px, 0.7fr) minmax(110px, 0.7fr)";

const LIST_HEIGHT = 420;
const ROW_HEIGHT = 52;
const OVERSCAN = 8;

const HeaderCell = ({ children }: { children: ReactNode }) => (
  <div className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">{children}</div>
);

type LogRowProps = {
  log: LogRecord;
  onRowClick: (log: LogRecord) => void;
  style?: CSSProperties;
};

const LogRow = memo(function LogRow({ log, onRowClick, style }: LogRowProps) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: GRID_TEMPLATE,
        ...(style ?? {}),
      }}
      className="cursor-pointer border-b border-slate-100/70 bg-white px-4 text-xs text-slate-600 transition hover:bg-slate-50"
      onClick={() => onRowClick(log)}
    >
      <div className="flex h-full items-center text-slate-500">
        {new Date(log.timestamp).toLocaleString()}
      </div>
      <div className="flex h-full items-center gap-2 capitalize">
        <span className={`h-2 w-2 rounded-full ${TRAFFIC_COLOR[log.traffic_light]}`} />
        {log.traffic_light}
      </div>
      <div className="flex h-full items-center text-slate-700">{log.http_status ?? "—"}</div>
      <div className="flex h-full items-center text-slate-700">{log.latency_ms ?? "—"}</div>
      <div className="flex h-full items-center text-slate-700">{log.ping_ms ?? "—"}</div>
      <div className="flex h-full items-center text-slate-700">{log.ssl_days_left ?? "—"}</div>
      <div className="flex h-full items-center text-slate-700">{log.dns_resolved ? "yes" : "no"}</div>
      <div className="flex h-full items-center text-slate-700">{log.redirects ?? "—"}</div>
    </div>
  );
});

const rowKey = (log: LogRecord, index: number) =>
  `${log.timestamp ?? index}-${log.url ?? ""}-${log.http_status ?? ""}-${log.traffic_light}`;

const RegularRows = memo(function RegularRows({
  logs,
  onRowClick,
}: {
  logs: LogRecord[];
  onRowClick: (log: LogRecord) => void;
}) {
  return (
    <div className="max-h-[420px] overflow-y-auto">
      {logs.map((log, index) => (
        <LogRow key={rowKey(log, index)} log={log} onRowClick={onRowClick} />
      ))}
    </div>
  );
});

const VirtualizedRows = memo(function VirtualizedRows({
  logs,
  onRowClick,
}: {
  logs: LogRecord[];
  onRowClick: (log: LogRecord) => void;
}) {
  const [scrollTop, setScrollTop] = useState(0);

  const handleScroll = useCallback((event: UIEvent<HTMLDivElement>) => {
    setScrollTop(event.currentTarget.scrollTop);
  }, []);

  const { start, end } = useMemo(() => {
    const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
    const endIndex = Math.min(
      logs.length,
      Math.ceil((scrollTop + LIST_HEIGHT) / ROW_HEIGHT) + OVERSCAN,
    );

    return { start: startIndex, end: endIndex };
  }, [logs.length, scrollTop]);

  const visibleLogs = useMemo(() => logs.slice(start, end), [logs, start, end]);

  return (
    <div className="max-h-[420px] overflow-y-auto" onScroll={handleScroll}>
      <div style={{ height: logs.length * ROW_HEIGHT, position: "relative" }}>
        <div
          style={{
            position: "absolute",
            top: start * ROW_HEIGHT,
            left: 0,
            right: 0,
          }}
        >
          {visibleLogs.map((log, index) => (
            <LogRow
              key={rowKey(log, start + index)}
              log={log}
              onRowClick={onRowClick}
              style={{ height: ROW_HEIGHT }}
            />
          ))}
        </div>
      </div>
    </div>
  );
});

export const LogsTable = memo(function LogsTable({
  logs,
  onRowClick,
  filters,
  onToggleTraffic,
  onStatusChange,
  onSearchChange,
  onLimitChange,
}: LogsTableProps) {
  const isVirtualized = logs.length > 1000;

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-200/60 bg-white/85 p-4 shadow-sm backdrop-blur">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <div className="flex flex-wrap gap-2">
          {TRAFFIC_ORDER.map((item) => {
            const active = filters.traffic.has(item);
            return (
              <button
                key={item}
                type="button"
                onClick={() => onToggleTraffic(item)}
                className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs capitalize transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 ${
                  active
                    ? "border-slate-900 bg-slate-900 text-white"
                    : "border-slate-200 bg-white text-slate-600"
                }`}
              >
                <span className={`h-2 w-2 rounded-full ${TRAFFIC_COLOR[item]}`} />
                {TRAFFIC_LABELS[item]}
              </button>
            );
          })}
        </div>
        <div className="flex flex-col gap-1 text-xs text-slate-500">
          <span className="font-medium text-slate-600">HTTP статус</span>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={100}
              max={filters.statusRange.max}
              value={filters.statusRange.min}
              onChange={(event) =>
                onStatusChange({ min: Number(event.target.value), max: filters.statusRange.max })
              }
              className="h-8 w-20 rounded-md border border-slate-200 bg-white px-2 text-slate-600 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300"
            />
            <span>—</span>
            <input
              type="number"
              min={filters.statusRange.min}
              max={599}
              value={filters.statusRange.max}
              onChange={(event) =>
                onStatusChange({ min: filters.statusRange.min, max: Number(event.target.value) })
              }
              className="h-8 w-20 rounded-md border border-slate-200 bg-white px-2 text-slate-600 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300"
            />
          </div>
        </div>
        <div className="flex flex-col gap-1 text-xs text-slate-500">
          <span className="font-medium text-slate-600">Поиск по URL</span>
          <input
            type="search"
            value={filters.search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Введите часть адреса"
            className="h-8 rounded-md border border-slate-200 bg-white px-3 text-slate-600 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300"
          />
        </div>
        <div className="flex flex-col gap-1 text-xs text-slate-500">
          <span className="font-medium text-slate-600">Лимит записей</span>
          <div className="flex items-center gap-2">
            {LIMIT_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => onLimitChange(option)}
                className={`h-8 w-12 rounded-md border text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300 ${
                  filters.limit === option
                    ? "border-slate-900 bg-slate-900 text-white"
                    : "border-slate-200 bg-white text-slate-600"
                }`}
              >
                {option}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200/70">
        <div className="min-w-[960px]">
          <div
            className="sticky top-0 z-10 grid bg-white/95 text-left"
            style={{ gridTemplateColumns: GRID_TEMPLATE }}
          >
            <HeaderCell>Время</HeaderCell>
            <HeaderCell>Статус</HeaderCell>
            <HeaderCell>HTTP</HeaderCell>
            <HeaderCell>Латентность</HeaderCell>
            <HeaderCell>Пинг</HeaderCell>
            <HeaderCell>SSL (дн.)</HeaderCell>
            <HeaderCell>DNS</HeaderCell>
            <HeaderCell>Редиректы</HeaderCell>
          </div>
          {isVirtualized ? (
            <VirtualizedRows logs={logs} onRowClick={onRowClick} />
          ) : (
            <RegularRows logs={logs} onRowClick={onRowClick} />
          )}
        </div>
      </div>
    </div>
  );
});
