import { type MouseEventHandler } from "react";
import { NodeToolbar, type NodeProps } from "reactflow";
import { useFlowStore } from "../../state/store";
import BaseBlock from "./BaseBlock";

import {
  buildWebsiteMetadata,
  DEFAULT_PING_INTERVAL,
  MAX_PING_INTERVAL,
  MIN_PING_INTERVAL,
  normalizePingInterval,
  type BaseNodeData,
} from "./types";

export default function WebsiteNode(props: NodeProps<BaseNodeData>) {
  const { data, id, selected } = props;

  const setSelectedNode = useFlowStore((state) => state.setSelectedNode);
  const updateNodeData = useFlowStore((state) => state.updateNodeData);
  const deleteSiteNode = useFlowStore((state) => state.deleteSiteNode);
  const removeNode = useFlowStore((state) => state.removeNode);

  const metadata = data.metadata ?? buildWebsiteMetadata(data);

  const handleEditClick: MouseEventHandler<HTMLButtonElement> = (event) => {
    event.stopPropagation();
    setSelectedNode(id);

    const state = useFlowStore.getState();
    const current = state.nodes.find((node) => node.id === id);
    if (!current || current.type !== "website") return;

    const currentUrl = current.data.description ?? "";
    const nextUrl = window.prompt("Введите URL сайта", currentUrl);
    if (nextUrl === null) return;
    const trimmedUrl = nextUrl.trim();

    const currentName = current.data.title ?? "";
    const nextName = window.prompt("Введите название сайта", currentName);
    if (nextName === null) return;
    const trimmedName = nextName.trim();

    const currentInterval = current.data.ping_interval ?? DEFAULT_PING_INTERVAL;
    const nextIntervalRaw = window.prompt(
      "Введите интервал опроса (сек)",
      String(currentInterval)
    );
    if (nextIntervalRaw === null) return;

    const normalizedInterval = normalizePingInterval(nextIntervalRaw);
    if (!normalizedInterval) {
      window.alert(
        `Интервал должен быть положительным числом от ${MIN_PING_INTERVAL} до ${MAX_PING_INTERVAL}`
      );
      return;
    }

    const updates: Partial<BaseNodeData> = {};
    if (trimmedUrl !== currentUrl && trimmedUrl !== "") {
      updates.description = trimmedUrl;
    }
    if (trimmedName !== currentName && trimmedName !== "") {
      updates.title = trimmedName;
    }
    if (normalizedInterval !== currentInterval) {
      updates.ping_interval = normalizedInterval;
    }

    if (Object.keys(updates).length > 0) {
      updateNodeData(id, updates);
    }
  };

  const handleDeleteClick: MouseEventHandler<HTMLButtonElement> = (event) => {
    event.stopPropagation();
    setSelectedNode(undefined);

    const state = useFlowStore.getState();
    const current = state.nodes.find((node) => node.id === id);
    if (!current || current.type !== "website") return;

    if (current.id.startsWith("temp-")) {
      removeNode(current.id);
      return;
    }

    void deleteSiteNode(current.id, Number(current.id));
  };

  return (
    <>
      <NodeToolbar isVisible={selected} position="top">
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600 shadow-sm transition hover:border-sky-300 hover:text-sky-600"
            onClick={handleEditClick}
          >
            ✏️ Изменить
          </button>
          <button
            type="button"
            className="rounded-full border border-rose-200 bg-white px-3 py-1 text-xs font-semibold text-rose-600 shadow-sm transition hover:border-rose-300 hover:text-rose-600"
            onClick={handleDeleteClick}
          >
            🗑 Удалить
          </button>
        </div>

      </NodeToolbar>
      <BaseBlock {...props} variant="website" data={{ ...data, metadata }} />
    </>
  );
}
