import type { Connection, Edge } from "reactflow";

import type { BlockVariant, FlowNode } from "../flow/nodes/types";

const forbiddenConnections: Partial<Record<BlockVariant, BlockVariant[]>> = {
  llm: ["website", "telegram"],
  messenger: ["llm", "website", "telegram"],
  telegram: ["llm", "website", "messenger"],
};

type ConnectionContext = {
  nodes: FlowNode[];
  edges: Edge[];
};

export function canConnect(connection: Connection, context: ConnectionContext): boolean {
  const { source, target } = connection;

  if (!source || !target) {
    return false;
  }

  if (source === target) {
    return false;
  }

  const sourceNode = context.nodes.find((node) => node.id === source);
  const targetNode = context.nodes.find((node) => node.id === target);

  if (!sourceNode || !targetNode) {
    return false;
  }

  const sourceType = sourceNode.type as BlockVariant | undefined;
  const targetType = targetNode.type as BlockVariant | undefined;

  if (!sourceType || !targetType) {
    return false;
  }

  const restrictedTargets = forbiddenConnections[sourceType];

  if (restrictedTargets?.includes(targetType)) {
    return false;
  }

  const hasDuplicateEdge = context.edges.some(
    (edge) => edge.source === source && edge.target === target
  );

  if (hasDuplicateEdge) {
    return false;
  }

  return true;
}
