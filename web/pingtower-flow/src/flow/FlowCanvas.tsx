import React from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  applyNodeChanges,
  applyEdgeChanges,
} from "reactflow";
import type { Node, Edge, NodeChange, EdgeChange } from "reactflow";

import "reactflow/dist/style.css";

import WebsiteNode from "./nodes/WebsiteNode";
import LLMNode from "./nodes/LLMNode";
import MessengerNode from "./nodes/MessengerNode";
import { useFlowStore } from "../state/store";

const nodeTypes = {
  website: WebsiteNode,
  llm: LLMNode,
  messenger: MessengerNode,
};

export default function FlowCanvas() {
  const { nodes, edges, setNodes, setEdges, onConnect } = useFlowStore();

  const handleNodesChange = (changes: NodeChange[]) => {
    setNodes((nds: Node[]) => applyNodeChanges(changes, nds));
  };

  const handleEdgesChange = (changes: EdgeChange[]) => {
    setEdges((eds: Edge[]) => applyEdgeChanges(changes, eds));
  };

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={handleNodesChange}
      onEdgesChange={handleEdgesChange}
      onConnect={onConnect}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.2 }}
    >
      <Background
        variant="dots"
        gap={24}
        size={2}
        color="#cbd5e1"
      />
      <Controls />
      <MiniMap maskColor="#f8fafc" nodeColor={() => "#0ea5e9"} />
    </ReactFlow>
  );
}
