import { useMemo, useState } from "react";
import clsx from "clsx";

import { NODE_LIBRARY } from "../flow/library";

const DASHBOARD_PRESETS = [
  {
    id: "main",
    title: "Основной дашборд",
    description: "Ключевые метрики продукта и бизнес-процессов в одном месте",
    emoji: "📊",
    stats: "10 виджетов",
    tone: "bg-sky-50 text-sky-600",
  },
];

function normalize(text: string) {
  return text.trim().toLowerCase();
}

function SectionToggle({
  title,
  subtitle,
  counter,
  isOpen,
  onToggle,
}: {
  title: string;
  subtitle?: string;
  counter?: string | number;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={clsx(
        "flex w-full items-center justify-between rounded-xl px-3 py-2 text-left",
        "transition focus:outline-none focus:ring-2 focus:ring-sky-200",
        isOpen ? "bg-slate-50/80" : "hover:bg-slate-50/60"
      )}
    >
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{title}</p>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3 text-slate-400">
        {typeof counter !== "undefined" && (
          <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-500">
            {counter}
          </span>
        )}
        <svg
          className={clsx(
            "h-3.5 w-3.5 transition-transform",
            isOpen ? "rotate-180" : "rotate-0"
          )}
          viewBox="0 0 16 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M4 6l4 4 4-4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    </button>
  );
}

export default function NodeLibrary() {
  const [query, setQuery] = useState("");
  const [dashboardsOpen, setDashboardsOpen] = useState(false);
  const [libraryOpen, setLibraryOpen] = useState(true);

  const filtered = useMemo(() => {
    const search = normalize(query);

    if (!search) {
      return NODE_LIBRARY;
    }

    return NODE_LIBRARY.filter((item) => {
      const haystack = `${item.data.title} ${item.data.description ?? ""}`;
      return normalize(haystack).includes(search);
    });
  }, [query]);

  const grouped = useMemo(() => {
    return filtered.reduce<Record<string, typeof filtered>>((acc, item) => {
      if (!acc[item.category]) {
        acc[item.category] = [];
      }
      acc[item.category].push(item);
      return acc;
    }, {});
  }, [filtered]);

  const handleDragStart = (templateId: string) => (event: React.DragEvent) => {
    event.dataTransfer.setData("application/reactflow/template", templateId);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <aside className="hidden w-72 flex-none flex-col border-r border-slate-200 bg-white/85 px-5 pb-6 pt-5 backdrop-blur lg:flex lg:overflow-y-auto">
      <div className="flex flex-1 flex-col gap-4 pb-4">
        <div>
          <SectionToggle
            title="Дашборды"
            subtitle="Готовые подборки для быстрого старта"
            counter={DASHBOARD_PRESETS.length}
            isOpen={dashboardsOpen}
            onToggle={() => setDashboardsOpen((prev) => !prev)}
          />
          <div
            className={clsx(
              "grid gap-3 overflow-hidden px-1 pt-3 text-sm transition-all duration-300 ease-in-out",
              dashboardsOpen
                ? "max-h-[420px] opacity-100"
                : "pointer-events-none max-h-0 -translate-y-2 opacity-0"
            )}
          >
            {DASHBOARD_PRESETS.map((dashboard) => (
              <button
                key={dashboard.id}
                type="button"
                className="group flex items-start gap-3 rounded-2xl border border-slate-200 bg-white px-3 py-3 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-sky-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-sky-200"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-lg">
                  {dashboard.emoji}
                </div>
                <div className="flex-1 space-y-1">
                  <p className="text-sm font-semibold text-slate-700">{dashboard.title}</p>
                  <p className="text-xs text-slate-500">{dashboard.description}</p>
                  <span
                    className={clsx(
                      "inline-flex items-center rounded-full px-2 py-1 text-[11px] font-semibold",
                      dashboard.tone
                    )}
                  >
                    {dashboard.stats}
                  </span>
                </div>
                <span className="opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                  ➜
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1">
          <SectionToggle
            title="Библиотека"
            subtitle="Перетащите блок на канвас"
            counter={filtered.length}
            isOpen={libraryOpen}
            onToggle={() => setLibraryOpen((prev) => !prev)}
          />

          <div
            className={clsx(
              "overflow-hidden transition-all duration-300 ease-in-out",
              libraryOpen
                ? "max-h-[960px] opacity-100"
                : "pointer-events-none max-h-0 -translate-y-2 opacity-0"
            )}
          >
            <label className="mt-4 flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus-within:border-sky-300 focus-within:ring-2 focus-within:ring-sky-200">
              <span className="text-slate-400">🔍</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Поиск..."
                className="w-full bg-transparent text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none"
              />
            </label>

            <div className="mt-5 flex flex-1 flex-col gap-6 pr-1">
              {Object.entries(grouped).map(([category, nodes]) => (
                <section key={category} className="space-y-3">
                  <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                    {category}
                  </h3>
                  <div className="space-y-2">
                    {nodes.map((node) => (
                      <button
                        key={node.templateId}
                        type="button"
                        onDragStart={handleDragStart(node.templateId)}
                        draggable
                        className={clsx(
                          "group w-full rounded-2xl border border-slate-200 bg-white px-3 py-3 text-left",
                          "shadow-sm transition-all hover:-translate-y-0.5 hover:border-sky-300 hover:shadow-md",
                          "focus:outline-none focus:ring-2 focus:ring-sky-200"
                        )}
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-lg">
                            {node.data.emoji}
                          </div>
                          <div className="flex-1">
                            <p className="text-sm font-semibold text-slate-700">
                              {node.data.title}
                            </p>
                            {node.data.description && (
                              <p className="mt-1 text-xs text-slate-500">
                                {node.data.description}
                              </p>
                            )}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </section>
              ))}

              {filtered.length === 0 && (
                <div className="flex flex-1 flex-col items-center justify-center text-center text-sm text-slate-400">
                  Ничего не найдено
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
