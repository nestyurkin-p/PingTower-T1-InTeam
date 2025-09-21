import type { Edge, Node } from "reactflow";

// Варианты блоков
export type BlockVariant = "website" | "llm" | "messenger" | "telegram";

// Статусы нод
export type NodeStatus = "idle" | "running" | "success" | "error";

// Метаданные
export type NodeMetadataEntry = {
  label: string;
  value: string;
};

// Базовые данные ноды
export const DEFAULT_PING_INTERVAL = 30;
export const MIN_PING_INTERVAL = 1;
export const MAX_PING_INTERVAL = 3600;


export type BaseNodeData = {
  title?: string;
  description?: string;
  emoji?: string;
  status?: NodeStatus;
  metadata?: NodeMetadataEntry[];
  ping_interval?: number;
  com?: Record<string, unknown> | null;

};

export function normalizePingInterval(value: string): number | undefined {
  const numeric = Number(value.trim());
  if (!Number.isFinite(numeric)) return undefined;
  if (numeric <= 0) return undefined;
  return Math.min(MAX_PING_INTERVAL, Math.max(MIN_PING_INTERVAL, Math.round(numeric)));
}

export function buildWebsiteMetadata(data: BaseNodeData): NodeMetadataEntry[] {
  const interval = data.ping_interval ?? DEFAULT_PING_INTERVAL;

  const entries: NodeMetadataEntry[] = [

    { label: "URL", value: data.description ?? "—" },
    { label: "Название", value: data.title ?? "Без имени" },
    { label: "Интервал", value: `${interval} сек` },
  ];

  const telegramStatusRaw =
    data.com && typeof data.com === "object" && "tg" in data.com
      ? (data.com as Record<string, unknown>).tg
      : undefined;

  if (telegramStatusRaw !== undefined) {
    const isEnabled = Number(telegramStatusRaw) === 1 || telegramStatusRaw === true;
    entries.push({ label: "Telegram", value: isEnabled ? "Подключен" : "Отключен" });
  }

  return entries;

}

// FlowNode
export type FlowNode = Node<BaseNodeData>;

// Состояние стора
export type FlowStore = {
  flowName: string;
  setFlowName: (name: string) => void;

  nodes: FlowNode[];
  edges: Edge[];

  runFlow: () => void;
  stopFlow: () => void;
  saveFlow: () => void;

  isRunning: boolean;
  isDirty: boolean;
  lastRunAt?: Date;
  lastSavedAt?: Date;
};
