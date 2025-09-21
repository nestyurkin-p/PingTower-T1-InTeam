import type { NodeProps } from "reactflow";

import BaseBlock from "./BaseBlock";
import type { BaseNodeData } from "./types";

export default function LLMNode(props: NodeProps<BaseNodeData>) {
  return <BaseBlock {...props} variant="llm" />;
}
