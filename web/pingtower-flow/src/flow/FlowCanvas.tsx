import React, { useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  MarkerType,
} from "reactflow";
import type { NodeChange, EdgeChange, Connection } from "reactflow";
import "reactflow/dist/style.css";

import WebsiteNode from "./nodes/WebsiteNode";
import LLMNode from "./nodes/LLMNode";
import MessengerNode from "./nodes/MessengerNode";
import { useFlowStore } from "../state/store";

const nodeTypes = { website: WebsiteNode, llm: LLMNode, messenger: MessengerNode };

export default function FlowCanvas() {
  const { nodes, edges, setNodes, setEdges } = useFlowStore();

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [setNodes]
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [setEdges]
  );

  const onConnect = useCallback(
    (c: Connection) =>
      setEdges((eds) =>
        addEdge(
          {
            ...c,
            type: "smoothstep",
            animated: true,
            style: { stroke: "#0ea5e9", strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: "#0ea5e9" },
          },
          eds
        )
      ),
    [setEdges]
  );

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      fitView
      defaultEdgeOptions={{
        type: "smoothstep",
        animated: true,
        style: { stroke: "#0ea5e9", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#0ea5e9" },
      }}
      connectionLineType="smoothstep"
      snapToGrid
      snapGrid={[20, 20]}
    >
      <Background variant="dots" gap={24} size={1} color="#cbd5e1" />
      <Controls />
      <MiniMap maskColor="#f8fafc" nodeColor={() => "#0ea5e9"} />
    </ReactFlow>
  );
}
