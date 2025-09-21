import { create } from "zustand";
import {
  fetchSites,
  createSite,
  updateSite,
  deleteSite,
  patchSiteParams,
  type SiteRecord,
} from "../lib/api";

import {
  type BaseNodeData,
  type FlowNode,
  buildWebsiteMetadata,
  DEFAULT_PING_INTERVAL,

  MAX_PING_INTERVAL,
  MIN_PING_INTERVAL,
  normalizePingInterval,
} from "../flow/nodes/types";
import type { Edge, XYPosition } from "reactflow";

export type NodeStatus = "idle" | "running" | "success" | "error";

const websiteSyncTimers = new Map<string, ReturnType<typeof setTimeout>>();

const cancelWebsiteSyncTimer = (nodeId: string) => {
  const timer = websiteSyncTimers.get(nodeId);
  if (timer) {
    clearTimeout(timer);
    websiteSyncTimers.delete(nodeId);
  }
};

const parseComValue = (value: SiteRecord["com"]): Record<string, unknown> | null => {
  if (!value) return null;
  if (typeof value === "string") {
    try {
      return JSON.parse(value) as Record<string, unknown>;
    } catch (err) {
      console.warn("[FlowStore] Не удалось распарсить поле com", err);
      return null;
    }
  }

  if (typeof value === "object") {
    return value as Record<string, unknown>;
  }

  return null;
};

const isTelegramLinked = (data?: BaseNodeData): boolean => {
  if (!data?.com || typeof data.com !== "object") return false;
  const raw = (data.com as Record<string, unknown>).tg;
  return Number(raw) === 1 || raw === true;
};

const buildTelegramCom = (
  current: BaseNodeData["com"],
  enabled: boolean
): Record<string, unknown> => {
  const base =
    current && typeof current === "object"
      ? { ...(current as Record<string, unknown>) }
      : ({} as Record<string, unknown>);
  base.tg = enabled ? 1 : 0;
  return base;
};

const isWebsiteConnectedToTelegram = (siteId: string, nodes: FlowNode[], edges: Edge[]): boolean => {
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));
  return edges.some((edge) => {
    if (edge.source !== siteId) return false;
    const targetNode = nodeMap.get(edge.target);
    return targetNode?.type === "telegram";
  });
};


type FlowStore = {
  flowName: string;
  setFlowName: (name: string) => void;

  nodes: FlowNode[];
  edges: Edge[];
  setNodes: (updater: FlowNode[] | ((nodes: FlowNode[]) => FlowNode[])) => void;
  setEdges: (updater: Edge[] | ((edges: Edge[]) => Edge[])) => void;
  setWebsiteTelegramLink: (siteId: string, enabled: boolean) => Promise<void>;

  selectedNodeId?: string;
  setSelectedNode: (id?: string) => void;

  initFromDb: () => Promise<void>;
  createWebsiteNode: (position: XYPosition, template: BaseNodeData) => Promise<FlowNode | undefined>;
  saveSite: (node: FlowNode) => Promise<SiteRecord | undefined>;

  deleteSiteNode: (nodeId: string, siteId: number) => Promise<void>;
  syncWebsiteNode: (node: FlowNode) => Promise<SiteRecord | undefined>;
  updateNodeData: (id: string, data: Partial<BaseNodeData>) => void;
  removeNode: (nodeId: string) => void;

  runFlow: () => void;
  stopFlow: () => void;
  saveFlow: () => void;

  isRunning: boolean;
  isDirty: boolean;
  lastRunAt?: Date;
  lastSavedAt?: Date;
};

export const useFlowStore = create<FlowStore>((set, get) => ({
  flowName: "Новый сценарий",
  setFlowName: (name) => set({ flowName: name, isDirty: true }),

  nodes: [],
  edges: [],
  setNodes: (updater) =>
    set((state) => ({
      nodes: typeof updater === "function" ? updater(state.nodes) : updater,
      isDirty: true,
    })),
  setEdges: (updater) => {
    const updates: { siteId: string; enabled: boolean }[] = [];

    set((state) => {
      const nextEdges =
        typeof updater === "function" ? updater(state.edges) : updater;

      const nodeMap = new Map(state.nodes.map((node) => [node.id, node]));
      const websiteFlags = new Map<string, boolean>();

      state.nodes.forEach((node) => {
        if (node.type === "website") {
          websiteFlags.set(node.id, false);
        }
      });

      nextEdges.forEach((edge) => {
        const sourceNode = nodeMap.get(edge.source);
        const targetNode = nodeMap.get(edge.target);

        if (sourceNode?.type === "website" && targetNode?.type === "telegram") {
          websiteFlags.set(sourceNode.id, true);
        }
      });

      websiteFlags.forEach((enabled, siteId) => {
        const node = nodeMap.get(siteId);
        if (!node) return;

        const currentlyLinked = isTelegramLinked(node.data);
        if (enabled !== currentlyLinked) {
          updates.push({ siteId, enabled });
        }
      });

      return { edges: nextEdges, isDirty: true };
    });

    updates.forEach(({ siteId, enabled }) => {
      void get().setWebsiteTelegramLink(siteId, enabled);
    });
  },

  selectedNodeId: undefined,
  setSelectedNode: (id) => set({ selectedNodeId: id }),

  // 📥 загрузка из БД
  initFromDb: async () => {
    try {
      const sites = await fetchSites();
      const nodes: FlowNode[] = sites.map((site) => {
        const com = parseComValue(site.com);
        const pingInterval = site.ping_interval ?? DEFAULT_PING_INTERVAL;

        return {
          id: String(site.id),
          type: "website",
          position: { x: Math.random() * 400, y: Math.random() * 400 },
          data: {
            title: site.name,
            description: site.url,
            emoji: "🌐",
            status: "idle" as NodeStatus,
            ping_interval: pingInterval,
            com,
            metadata: buildWebsiteMetadata({
              title: site.name,
              description: site.url,
              ping_interval: pingInterval,
              com,
            }),
          },
        };
      });
      set({ nodes, isDirty: false });
    } catch (err) {
      console.error("[FlowStore] Ошибка загрузки сайтов:", err);
    }
  },

  createWebsiteNode: async (position, template) => {
    if (typeof window === "undefined") return;

    const defaultUrl = template.description?.trim() || "https://example.com";
    const defaultName = template.title?.trim() || "Новый сайт";
    const defaultInterval = template.ping_interval ?? DEFAULT_PING_INTERVAL;

    const urlInput = window.prompt("Введите URL сайта", defaultUrl);
    if (urlInput === null) return;
    const url = urlInput.trim();
    if (!url) {
      window.alert("URL не может быть пустым");
      return;
    }

    const nameInput = window.prompt("Введите название сайта", defaultName);
    if (nameInput === null) return;
    const name = nameInput.trim();
    if (!name) {
      window.alert("Название не может быть пустым");
      return;
    }

    const intervalInput = window.prompt(
      "Введите интервал опроса (сек)",
      String(defaultInterval)
    );
    if (intervalInput === null) return;

    const normalizedInterval = normalizePingInterval(intervalInput);
    if (!normalizedInterval) {
      window.alert(
        `Интервал должен быть положительным числом от ${MIN_PING_INTERVAL} до ${MAX_PING_INTERVAL}`
      );
      return;
    }

    try {
      const saved = await createSite(url, name, normalizedInterval);
      const com = parseComValue(saved.com) ?? buildTelegramCom(template.com, false);

      const node: FlowNode = {
        id: String(saved.id),
        type: "website",
        position,
        data: {

          emoji: template.emoji ?? "🌐",
          status: template.status ?? "idle",
          title: saved.name,
          description: saved.url,
          ping_interval: saved.ping_interval ?? normalizedInterval,
          com,
          metadata: buildWebsiteMetadata({
            title: saved.name,
            description: saved.url,
            ping_interval: saved.ping_interval ?? normalizedInterval,
            com,

          }),
        },
      };

      set((state) => ({
        nodes: state.nodes.concat(node),
        selectedNodeId: node.id,
        isDirty: false,
        lastSavedAt: new Date(),
      }));

      return node;
    } catch (err) {
      console.error("[FlowStore] Ошибка создания сайта:", err);
    }
  },

  createWebsiteNode: async (position, template) => {
    if (typeof window === "undefined") return;

    const defaultUrl = template.description?.trim() || "https://example.com";
    const defaultName = template.title?.trim() || "Новый сайт";
    const defaultInterval = template.ping_interval ?? DEFAULT_PING_INTERVAL;

    const urlInput = window.prompt("Введите URL сайта", defaultUrl);
    if (urlInput === null) return;
    const url = urlInput.trim();
    if (!url) {
      window.alert("URL не может быть пустым");
      return;
    }

    const nameInput = window.prompt("Введите название сайта", defaultName);
    if (nameInput === null) return;
    const name = nameInput.trim();
    if (!name) {
      window.alert("Название не может быть пустым");
      return;
    }

    const intervalInput = window.prompt(
      "Введите интервал опроса (сек)",
      String(defaultInterval)
    );
    if (intervalInput === null) return;

    const normalizedInterval = normalizePingInterval(intervalInput);
    if (!normalizedInterval) {
      window.alert(
        `Интервал должен быть положительным числом от ${MIN_PING_INTERVAL} до ${MAX_PING_INTERVAL}`
      );
      return;
    }

    try {
      const saved = await createSite(url, name, normalizedInterval);


      const node: FlowNode = {
        id: String(saved.id),
        type: "website",
        position,
        data: {
          emoji: template.emoji ?? "🌐",
          status: template.status ?? "idle",
          title: saved.name,
          description: saved.url,

          ping_interval: saved.ping_interval ?? normalizedInterval,
          metadata: buildWebsiteMetadata({
            title: saved.name,
            description: saved.url,
            ping_interval: saved.ping_interval ?? normalizedInterval,

          }),
        },
      };

      set((state) => ({
        nodes: state.nodes.concat(node),
        selectedNodeId: node.id,
        isDirty: false,
        lastSavedAt: new Date(),
      }));

      return node;
    } catch (err) {
      console.error("[FlowStore] Ошибка создания сайта:", err);
    }
  },

  // 💾 сохранить / обновить сайт
  saveSite: async (node) => {
    if (node.type !== "website") return;

    try {
      const url = node.data.description || "";
      const name = node.data.title || "Без имени";
      const ping_interval = node.data.ping_interval ?? DEFAULT_PING_INTERVAL;

      const saved = node.id.startsWith("temp-")
        ? await createSite(url, name, ping_interval)
        : await updateSite(Number(node.id), { url, name, ping_interval });
      const com = parseComValue(saved.com) ?? node.data.com ?? null;

      set((state) => ({
        nodes: state.nodes.map((n) =>
          n.id === node.id
            ? {
                ...n,
                id: String(saved.id),
                data: {
                  ...n.data,
                  title: saved.name,
                  description: saved.url,
                  com,

                  metadata: buildWebsiteMetadata({
                    title: saved.name,
                    description: saved.url,
                    ping_interval: saved.ping_interval,
                    com,

                  }),
                },
              }
            : n
        ),
        isDirty: false,
        lastSavedAt: new Date(),
      }));

      return saved;
    } catch (err) {
      console.error("[FlowStore] Ошибка сохранения сайта:", err);
    }
  },

  // 🗑 удалить сайт
  deleteSiteNode: async (nodeId, siteId) => {
    try {
      await deleteSite(Number(siteId));
    } catch (err) {
      console.warn("[FlowStore] Сервер не нашёл сайт, удаляем только локально", { nodeId, siteId, err });
    } finally {
      cancelWebsiteSyncTimer(nodeId);
      set((state) => ({
        nodes: state.nodes.filter((n) => n.id !== nodeId),
        isDirty: true,
      }));
      get().setEdges((edges) => edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
    }
  },

  // 🔄 синхронизация
  syncWebsiteNode: async (node) => {
    if (node.type === "website") {
      return await get().saveSite(node);
    }
  },

  setWebsiteTelegramLink: async (siteId, enabled) => {
    const state = get();
    const node = state.nodes.find((candidate) => candidate.id === siteId && candidate.type === "website");
    if (!node) return;

    const numericId = Number(siteId);
    if (!Number.isFinite(numericId)) return;

    const desiredState = isWebsiteConnectedToTelegram(siteId, state.nodes, state.edges);
    if (enabled !== desiredState) {
      enabled = desiredState;
    }

    const currentlyLinked = isTelegramLinked(node.data);
    if (enabled === currentlyLinked) return;

    const nextCom = buildTelegramCom(node.data.com, enabled);

    try {
      const saved = await patchSiteParams(numericId, { com: nextCom });
      const savedCom = parseComValue(saved.com) ?? nextCom;

      set((innerState) => ({
        nodes: innerState.nodes.map((candidate) =>
          candidate.id === siteId && candidate.type === "website"
            ? {
                ...candidate,
                data: {
                  ...candidate.data,
                  com: savedCom,
                  metadata: buildWebsiteMetadata({
                    ...candidate.data,
                    com: savedCom,
                  }),
                },
              }
            : candidate
        ),
        lastSavedAt: new Date(),
      }));

      const latest = get();
      const shouldBeEnabledNow = isWebsiteConnectedToTelegram(siteId, latest.nodes, latest.edges);
      const latestNode = latest.nodes.find(
        (candidate) => candidate.id === siteId && candidate.type === "website"
      );
      const latestLinked = isTelegramLinked(latestNode?.data);

      if (shouldBeEnabledNow !== latestLinked) {
        void get().setWebsiteTelegramLink(siteId, shouldBeEnabledNow);
      }
    } catch (err) {
      console.error("[FlowStore] Ошибка обновления привязки Telegram", {
        siteId,
        enabled,
        err,
      });
    }
  },

  // ✏️ обновить локально
  updateNodeData: (id, data) => {
    let updatedNode: FlowNode | undefined;

    set((state) => ({
      nodes: state.nodes.map((node) => {
        if (node.id !== id) return node;

        const nextData: BaseNodeData = {
          ...node.data,
          ...data,
        };

        if (node.type === "website") {
          nextData.metadata = buildWebsiteMetadata(nextData);
        }

        const nextNode = { ...node, data: nextData };
        updatedNode = nextNode;
        return nextNode;
      }),
      isDirty: true,
    }));

    const shouldSyncWebsite =
      updatedNode?.type === "website" &&
      ("title" in data || "description" in data || "ping_interval" in data);

    if (updatedNode && shouldSyncWebsite) {
      const existingTimer = websiteSyncTimers.get(updatedNode.id);
      if (existingTimer) {
        clearTimeout(existingTimer);
      }

      const timer = setTimeout(() => {
        void get().syncWebsiteNode(updatedNode!);
        websiteSyncTimers.delete(updatedNode!.id);
      }, 500);

      websiteSyncTimers.set(updatedNode.id, timer);
    }
  },

  removeNode: (nodeId) => {
    cancelWebsiteSyncTimer(nodeId);
    set((state) => ({
      nodes: state.nodes.filter((node) => node.id !== nodeId),
      isDirty: true,
    }));
    get().setEdges((edges) => edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));

  },

  runFlow: () => set({ isRunning: true, lastRunAt: new Date() }),
  stopFlow: () => set({ isRunning: false }),

  saveFlow: () => set({ isDirty: false, lastSavedAt: new Date() }),

  isRunning: false,
  isDirty: false,
  lastRunAt: undefined,
  lastSavedAt: undefined,
}));
