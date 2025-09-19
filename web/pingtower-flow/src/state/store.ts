import { create } from "zustand";
import type { Node, Edge } from "reactflow";

type Store = {
  nodes: Node[];
  edges: Edge[];
  setNodes: (updater: (nds: Node[]) => Node[]) => void;
  setEdges: (updater: (eds: Edge[]) => Edge[]) => void;
};

export const useFlowStore = create<Store>((set) => ({
  nodes: [
    { id: "1", type: "website",   position: { x: 80,  y: 140 }, data: { title: "Website",   emoji: "🌐" } },
    { id: "2", type: "llm",       position: { x: 360, y: 140 }, data: { title: "LLM",       emoji: "🤖" } },
    { id: "3", type: "messenger", position: { x: 640, y: 140 }, data: { title: "Messenger", emoji: "💬" } },
  ],
  edges: [],
  setNodes: (updater) => set((s) => ({ nodes: updater(s.nodes) })),
  setEdges: (updater) => set((s) => ({ edges: updater(s.edges) })),
}));
