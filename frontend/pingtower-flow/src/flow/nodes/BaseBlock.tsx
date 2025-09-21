import { type CSSProperties } from "react";
import clsx from "clsx";
import { Handle, Position, type NodeProps } from "reactflow";

import type { BaseNodeData, BlockVariant, NodeStatus } from "./types";

const variantStyles: Record<
  BlockVariant,
  {
    border: string;
    glow: string;
    accent: string;
    size: { width: number; height: number; radius: string };
  }
> = {
  website: {
    border: "border-sky-200",
    glow: "shadow-[0_10px_30px_-15px_rgba(14,165,233,0.45)]",
    accent: "bg-sky-500/10 text-sky-600 border-sky-200",
    size: { width: 220, height: 170, radius: "rounded-2xl" },
  },
  llm: {
    border: "border-violet-200",
    glow: "shadow-[0_10px_32px_-18px_rgba(139,92,246,0.55)]",
    accent: "bg-violet-500/10 text-violet-600 border-violet-200",
    size: { width: 210, height: 160, radius: "rounded-3xl" },
  },
  messenger: {
    border: "border-emerald-200",
    glow: "shadow-[0_10px_32px_-18px_rgba(16,185,129,0.55)]",
    accent: "bg-emerald-500/10 text-emerald-600 border-emerald-200",
    size: { width: 210, height: 160, radius: "rounded-2xl" },
  },
  telegram: {
    border: "border-emerald-200",
    glow: "shadow-[0_10px_32px_-18px_rgba(16,185,129,0.55)]",
    accent: "bg-emerald-500/10 text-emerald-600 border-emerald-200",
    size: { width: 210, height: 160, radius: "rounded-2xl" },
  },
};

const statusStyles: Record<
  NodeStatus,
  { label: string; className: string; dot: string }
> = {
  idle: {
    label: "Ожидание",
    className: "border-slate-200 bg-slate-50 text-slate-500",
    dot: "bg-slate-400",
  },
  running: {
    label: "Выполняется",
    className: "border-amber-200 bg-amber-50 text-amber-600",
    dot: "bg-amber-400",
  },
  success: {
    label: "Готово",
    className: "border-emerald-200 bg-emerald-50 text-emerald-600",
    dot: "bg-emerald-500",
  },
  error: {
    label: "Ошибка",
    className: "border-rose-200 bg-rose-50 text-rose-600",
    dot: "bg-rose-400",
  },
};

const portClassName =
  "h-3.5 w-3.5 rounded-full border-2 border-white transition-transform duration-150 " +
  "hover:scale-125 shadow-[0_0_0_4px_rgba(15,23,42,0.18)]";

const portColors: Record<"source" | "target", string> = {
  source: "bg-sky-400 hover:bg-sky-500",
  target: "bg-slate-500 hover:bg-slate-600",
};

const HANDLE_OFFSET = 8;

function Port({ position, type }: { position: Position; type: "source" | "target" }) {
  const baseStyle: CSSProperties = {
    position: "absolute",
    ...(position === Position.Top && { top: 0, left: "50%" }),
    ...(position === Position.Bottom && { bottom: 0, left: "50%" }),
    ...(position === Position.Left && { left: 0, top: "50%" }),
    ...(position === Position.Right && { right: 0, top: "50%" }),
  };

  const transforms: string[] = [];

  if (position === Position.Top) {
    transforms.push("translate(-50%, -50%)");
    transforms.push(type === "source" ? `translateX(${HANDLE_OFFSET}px)` : `translateX(-${HANDLE_OFFSET}px)`);
  }

  if (position === Position.Bottom) {
    transforms.push("translate(-50%, 50%)");
    transforms.push(type === "source" ? `translateX(${HANDLE_OFFSET}px)` : `translateX(-${HANDLE_OFFSET}px)`);
  }

  if (position === Position.Left) {
    transforms.push("translate(-50%, -50%)");
    transforms.push(type === "source" ? `translateY(${HANDLE_OFFSET}px)` : `translateY(-${HANDLE_OFFSET}px)`);
  }

  if (position === Position.Right) {
    transforms.push("translate(50%, -50%)");
    transforms.push(type === "source" ? `translateY(${HANDLE_OFFSET}px)` : `translateY(-${HANDLE_OFFSET}px)`);
  }

  baseStyle.transform = transforms.join(" ");

  return (
    <Handle
      id={`${position}-${type}`}
      type={type}
      position={position}
      style={baseStyle}
      className={clsx(portClassName, portColors[type])}
      isConnectable
    />
  );
}

interface BaseBlockProps extends NodeProps<BaseNodeData> {
  variant: BlockVariant;
}

export default function BaseBlock({ variant, data, selected }: BaseBlockProps) {
  const config = variantStyles[variant];
  const status: NodeStatus = (data?.status as NodeStatus) ?? "idle";
  const statusConfig = statusStyles[status] ?? statusStyles.idle;

  return (
    <div
      style={{ width: config.size.width, height: config.size.height }}
      className={clsx(
        "group relative flex h-full w-full flex-col overflow-hidden",
        "bg-white/80 backdrop-blur border transition-all",
        config.size.radius,
        config.border,
        config.glow,
        selected ? "ring-2 ring-offset-2 ring-slate-500/40" : "ring-0"
      )}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-white/30 via-transparent to-white/0" />

      {/* Header */}
      <div className="relative flex items-center gap-3 px-5 pt-5">
        <div
          className={clsx(
            "flex h-11 w-11 items-center justify-center rounded-2xl border text-2xl",
            config.accent
          )}
        >
          {data?.emoji ?? "❓"}
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-slate-800">
            {data?.title ?? "Без имени"}
          </div>
          {data?.description && (
            <div className="truncate text-xs text-slate-500">{data.description}</div>
          )}
        </div>
        <div
          className={clsx(
            "flex items-center gap-2 rounded-full border px-3 py-1 text-[10px] font-semibold uppercase",
            statusConfig.className
          )}
        >
          <span className={clsx("h-1.5 w-1.5 rounded-full", statusConfig.dot)} />
          {statusConfig.label}
        </div>
      </div>

      {/* Metadata */}
      {Array.isArray(data?.metadata) && data.metadata.length > 0 && (
        <div className="relative mt-4 px-5">
          <dl className="grid grid-cols-2 gap-3 text-[11px] text-slate-600">
            {data.metadata.map((item, i) => (
              <div
                key={`${item.label}-${item.value}-${i}`}
                className="flex flex-col gap-1 rounded-xl bg-slate-50/70 p-2"
              >
                <dt className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  {item.label}
                </dt>
                <dd className="truncate text-xs text-slate-700">{item.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      <div className="relative flex-1" />

      {/* Ports */}
      <Port type="target" position={Position.Top} />
      <Port type="source" position={Position.Top} />
      <Port type="target" position={Position.Bottom} />
      <Port type="source" position={Position.Bottom} />
      <Port type="target" position={Position.Left} />
      <Port type="source" position={Position.Left} />
      <Port type="target" position={Position.Right} />
      <Port type="source" position={Position.Right} />
    </div>
  );
}
