import { BadgeCheck, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";


export type IncidentBannerProps = {
  incidentCount: number;
  windowSize: number;
  onClick?: () => void;
  actionSlot?: ReactNode;
};

export function IncidentBanner({
  incidentCount,
  windowSize,
  onClick,
  actionSlot,
}: IncidentBannerProps) {
  if (incidentCount === 0) return null;

  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center justify-between rounded-xl border border-amber-300/70 bg-amber-50/80 p-4 text-left shadow-sm transition hover:border-amber-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
    >
      <div className="flex items-center gap-3">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-amber-100 text-amber-700">
          <TriangleAlert className="h-5 w-5" />
        </span>
        <div>
          <p className="text-sm font-semibold text-amber-800">Инциденты: {incidentCount}</p>
          <p className="text-xs text-amber-700/80">
            Найдено {incidentCount} событий с предупреждениями за последние {windowSize} записей.
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        {actionSlot}
        <BadgeCheck className="h-5 w-5 text-amber-600" />
      </div>
    </button>
  );
}
