import { Handle, Position } from "reactflow";
import type { NodeProps } from "reactflow";

export default function BaseBlock({ title, emoji }: NodeProps & { title: string; emoji: string }) {
  return (
    <div
      style={{ width: 160, height: 160 }}
      className="bg-white border border-slate-200 rounded-2xl shadow-md flex flex-col items-center justify-center hover:shadow-lg transition-shadow"
    >
      <div className="text-3xl mb-2">{emoji}</div>
      <div className="font-semibold text-slate-700">{title}</div>

      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-slate-300 rounded-full" />
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-slate-300 rounded-full" />
    </div>
  );
}
