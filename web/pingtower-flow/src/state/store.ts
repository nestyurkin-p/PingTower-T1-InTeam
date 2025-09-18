import { create } from "zustand";
import type { Node, Edge, Connection } from "reactflow";
import { nanoid } from "nanoid";
import { canConnect } from "../utils/validation";

type Store = {
  nodes: Node[];
  edges: Edge[];
  setNodes: (updater: (n: Node[]) => Node[]) => void;
  setEdges: (updater: (e: Edge[]) => Edge[]) => void;
  onConnect: (c: Connection) => void;
  addNode: (type: "website" | "llm" | "messenger", pos?: { x: number; y: number }) => void;
};

export const useFlowStore = create<Store>((set, get) => ({
  nodes: [
    { id: "1", type: "website", position: { x: 50, y: 100 }, data: {} },
    { id: "2", type: "llm", position: { x: 300, y: 100 }, data: {} },
    { id: "3", type: "messenger", position: { x: 550, y: 100 }, data: {} },
  ],

  edges: [],

  setNodes: (updater) => set(state => ({ nodes: updater(state.nodes) })),
  setEdges: (updater) => set(state => ({ edges: updater(state.edges) })),

  onConnect: (c) => {
    const { nodes } = get();
    const s = nodes.find(n => n.id === c.source);
    const t = nodes.find(n => n.id === c.target);
    if (!s || !t) return;
    if (!canConnect(s.type, t.type)) return;

    set(state => ({
      edges: [
        ...state.edges,
        {
          id: `e-${c.source}-${c.target}`,
          source: c.source!,
          target: c.target!,
          sourceHandle: c.sourceHandle ?? undefined,
          targetHandle: c.targetHandle ?? undefined,
          animated: true,
          style: { stroke: "#0ea5e9", strokeWidth: 2 },
        },
      ],
    }));
  },

  addNode: (type, pos = { x: 100, y: 100 }) =>
    set(state => ({
      nodes: [...state.nodes, { id: nanoid(6), type, position: pos, data: {} }],
    })),
}));
