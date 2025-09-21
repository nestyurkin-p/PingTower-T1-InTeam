import { useCallback, useMemo, useRef } from "react";
import { nanoid } from "nanoid";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Panel,
  ReactFlowProvider,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type ConnectionLineType,
  type EdgeChange,
  type Edge,
  type NodeChange,
  MarkerType,
  useReactFlow,
} from "reactflow";
import "reactflow/dist/style.css";

import { useShallow } from "zustand/react/shallow";

import { NODE_LIBRARY } from "./library";
import LLMNode from "./nodes/LLMNode";
import MessengerNode from "./nodes/MessengerNode";
import TelegramNode from "./nodes/TelegramNode";
import WebsiteNode from "./nodes/WebsiteNode";
import type { FlowNode } from "./nodes/types";
import { useFlowStore } from "../state/store";
import { canConnect } from "../utils/validation";
import SmartConnectionLine from "./edges/SmartConnectionLine";

const nodeTypes = {
  website: WebsiteNode,
  llm: LLMNode,
  messenger: MessengerNode,
  telegram: TelegramNode,
};

const EDGE_COLOR = "#38bdf8";

const defaultEdgeOptions = {
  type: "smoothstep" as const,
  animated: true,
  markerEnd: {
    type: MarkerType.ArrowClosed,
    color: EDGE_COLOR,
    width: 20,
    height: 20,
  },
  style: { stroke: EDGE_COLOR, strokeWidth: 2 },
};

const smoothstepLineType = "smoothstep" as ConnectionLineType;

type SelectionChangeParams = Parameters<
  NonNullable<React.ComponentProps<typeof ReactFlow>["onSelectionChange"]>
>[0];

function CanvasInner() {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const reactFlow = useReactFlow();

  // 🔹 Один вызов useFlowStore со всеми нужными данными
  const {
    nodes,
    edges,
    setNodes,
    setEdges,
    setSelectedNode,
    createWebsiteNode,
  } = useFlowStore(
    useShallow((state) => ({
      nodes: state.nodes,
      edges: state.edges,
      setNodes: state.setNodes,
      setEdges: state.setEdges,
      setSelectedNode: state.setSelectedNode,
      createWebsiteNode: state.createWebsiteNode,
    }))
  );

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [setNodes]
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [setEdges]
  );

  const buildEdge = useCallback(
    (connection: Connection): Edge => ({
      id: nanoid(),
      source: connection.source!,
      target: connection.target!,
      sourceHandle: connection.sourceHandle,
      targetHandle: connection.targetHandle,
      ...defaultEdgeOptions,
    }),
    []
  );

  const isValidConnection = useCallback(
    (connection: Connection) => canConnect(connection, { nodes, edges }),
    [nodes, edges]
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!isValidConnection(connection)) return;
      setEdges((eds) => eds.concat(buildEdge(connection)));
    },
    [buildEdge, isValidConnection, setEdges]
  );

  const onSelectionChange = useCallback(
    ({ nodes: selectedNodes }: SelectionChangeParams) => {
      const first = (selectedNodes as FlowNode[])[0];
      setSelectedNode(first?.id);
    },
    [setSelectedNode]
  );

  const onPaneClick = useCallback(() => setSelectedNode(undefined), [setSelectedNode]);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const templateId = event.dataTransfer.getData("application/reactflow/template");
      const template = NODE_LIBRARY.find((item) => item.templateId === templateId);
      if (!template) return;

      const position = reactFlow.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      if (template.type === "website") {
        void createWebsiteNode(position, template.data);
        return;
      }

      const newNode: FlowNode = {
        id: `temp-${nanoid()}`,
        type: template.type,
        position,
        data: { ...template.data },
      };

      setNodes((nds) => nds.concat(newNode));
      setSelectedNode(newNode.id);
    },
    [createWebsiteNode, reactFlow, setNodes, setSelectedNode]
  );

  const backgroundGap = useMemo(() => ({ x: 40, y: 40 }), []);

  return (
    <div ref={wrapperRef} className="relative flex h-full flex-1">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onSelectionChange={onSelectionChange}
        onPaneClick={onPaneClick}
        onDrop={onDrop}
        onDragOver={onDragOver}
        isValidConnection={isValidConnection}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionLineType={smoothstepLineType}
        connectionLineComponent={SmartConnectionLine}
        snapToGrid
        snapGrid={[24, 24]}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.4}
        maxZoom={1.6}
        selectionOnDrag
        className="bg-gradient-to-br from-slate-100 via-slate-100 to-slate-200"
      >
        <Background
          id="dots"
          variant={BackgroundVariant.Dots}
          gap={backgroundGap.x}
          size={1.5}
          color="#94a3b8"
        />
        <Controls showInteractive={false} position="bottom-left" />
        <Panel
          position="top-right"
          className="rounded-2xl border border-slate-200 bg-white/80 px-4 py-2 text-xs text-slate-500 shadow-sm backdrop-blur"
        >
          <span className="font-semibold text-slate-700">Подсказка:</span> перетащите блок из библиотеки слева
        </Panel>
      </ReactFlow>
    </div>
  );
}

export default function FlowCanvas() {
  return (
    <div className="relative flex-1 overflow-hidden">
      <ReactFlowProvider>
        <CanvasInner />
      </ReactFlowProvider>
    </div>
  );
}
