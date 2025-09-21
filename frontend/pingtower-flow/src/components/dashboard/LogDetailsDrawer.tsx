import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import type { LogRecord } from "@/utils/stats";

export type LogDetailsDrawerProps = {
  log: LogRecord | null;
  open: boolean;
  onClose: () => void;
  latencyTrend: { timestamp: number; value: number }[];
  pingTrend: { timestamp: number; value: number }[];
};

const DrawerContent = ({
  log,
  onClose,
  latencyTrend,
  pingTrend,
}: Pick<LogDetailsDrawerProps, "log" | "onClose" | "latencyTrend" | "pingTrend">) => {
  if (!log) return null;

  return (
    <div className="pointer-events-auto ml-auto flex h-full w-full max-w-xl flex-col border-l border-slate-200 bg-white shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Детали проверки</h2>
          <p className="text-xs text-slate-500">{new Date(log.timestamp).toLocaleString()}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="space-y-4">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Статистика</h3>
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-200/70 p-3">
                <p className="text-xs font-medium text-slate-500">Латентность</p>
                <div className="mt-2 h-32">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={latencyTrend} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
                      <XAxis dataKey="timestamp" hide type="number" domain={["auto", "auto"]} />
                      <Tooltip
                        labelFormatter={(value) => new Date(value).toLocaleTimeString()}
                        formatter={(value: number) => [`${value} мс`, "Латентность"]}
                      />
                      <Line type="monotone" dataKey="value" stroke="#0f172a" strokeWidth={2} dot={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="rounded-xl border border-slate-200/70 p-3">
                <p className="text-xs font-medium text-slate-500">Пинг</p>
                <div className="mt-2 h-32">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={pingTrend} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
                      <XAxis dataKey="timestamp" hide type="number" domain={["auto", "auto"]} />
                      <Tooltip
                        labelFormatter={(value) => new Date(value).toLocaleTimeString()}
                        formatter={(value: number) => [`${value} мс`, "Пинг"]}
                      />
                      <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2} dot={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">JSON</h3>
            <pre className="mt-2 overflow-x-auto rounded-xl border border-slate-200/70 bg-slate-950/95 p-4 text-xs text-slate-200">
              {JSON.stringify(log, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};

export function LogDetailsDrawer({ log, open, onClose, latencyTrend, pingTrend }: LogDetailsDrawerProps) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex bg-slate-950/40 backdrop-blur-sm" onClick={onClose}>
      <div className="pointer-events-none flex h-full w-full" onClick={(event) => event.stopPropagation()}>
        <DrawerContent log={log} onClose={onClose} latencyTrend={latencyTrend} pingTrend={pingTrend} />
      </div>
    </div>,
    document.body,
  );
}
