import clsx from "clsx";

export type AppView = "dashboard" | "flow";

export default function AppNavigation({
  activeView,
  onChange,
}: {
  activeView: AppView;
  onChange: (view: AppView) => void;
}) {
  return (
    <header className="relative flex items-center justify-between gap-6 border-b border-slate-200 bg-white/85 px-6 py-4 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 via-indigo-500 to-blue-600 text-lg font-semibold text-white shadow-inner">
          PT
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-800">PingTower</p>
          <p className="text-xs text-slate-500">Платформа мониторинга</p>
        </div>
      </div>

      <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 p-1 text-sm font-medium text-slate-500 shadow-inner">
        <button
          type="button"
          onClick={() => onChange("dashboard")}
          className={clsx(
            "flex items-center gap-2 rounded-full px-4 py-2 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-200",
            activeView === "dashboard"
              ? "bg-white text-slate-900 shadow"
              : "hover:text-slate-700"
          )}
        >
          <span className="text-base">📊</span>
          Дашборд
        </button>
        <button
          type="button"
          onClick={() => onChange("flow")}
          className={clsx(
            "flex items-center gap-2 rounded-full px-4 py-2 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-200",
            activeView === "flow" ? "bg-white text-slate-900 shadow" : "hover:text-slate-700"
          )}
        >
          <span className="text-base">🧩</span>
          Конструктор
        </button>
      </div>
    </header>
  );
}
