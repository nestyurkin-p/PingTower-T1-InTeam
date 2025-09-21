import type { NodeProps } from "reactflow";

import BaseBlock from "./BaseBlock";
import type { BaseNodeData } from "./types";

export default function TelegramNode(props: NodeProps<BaseNodeData>) {
  return <BaseBlock {...props} variant="telegram" />;
}
