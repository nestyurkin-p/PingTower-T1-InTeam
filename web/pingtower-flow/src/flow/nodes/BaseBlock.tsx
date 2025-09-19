import { Handle, Position, type NodeProps } from "reactflow";

type BlockVariant = "website" | "llm" | "messenger";

const sizes: Record<BlockVariant, { w: number; h: number; radius: string }> = {
  website:   { w: 150, h: 150, radius: "rounded-xl"  },
  llm:       { w: 120, h: 120, radius: "rounded-3xl" },
  messenger: { w: 130, h: 130, radius: "rounded-2xl" },
};

// классы для красивых портов
const port =
  "w-3 h-3 rounded-full bg-slate-400 transition-all duration-200 ease-out " +
  "hover:bg-sky-500 hover:scale-125 hover:shadow-[0_0_6px_2px_rgba(14,165,233,0.4)]";

function Port({ pos }: { pos: Position }) {
  const baseStyle: React.CSSProperties = {
    position: "absolute",
    ...(pos === Position.Top    && { top: 0, left: "50%", transform: "translate(-50%, -50%)" }),
    ...(pos === Position.Bottom && { bottom: 0, left: "50%", transform: "translate(-50%, 50%)" }),
    ...(pos === Position.Left   && { left: 0, top: "50%", transform: "translate(-50%, -50%)" }),
    ...(pos === Position.Right  && { right: 0, top: "50%", transform: "translate(50%, -50%)" }),
  };

  return (
    <>
      {/* источник */}
      <Handle
        id={`${pos}-src`}
        type="source"
        position={pos}
        style={baseStyle}
        className={port}
        isConnectable
      />
      {/* приёмник */}
      <Handle
        id={`${pos}-tgt`}
        type="target"
        position={pos}
        style={baseStyle}
        className={port}
        isConnectable
      />
    </>
  );
}

export default function BaseBlock({
  type,
  data,
}: NodeProps & { type: BlockVariant; data: { title: string; emoji: string } }) {
  const { w, h, radius } = sizes[type];

  return (
    <div
      style={{ width: w, height: h }}
      className={`relative flex flex-col items-center justify-center 
                  bg-white border border-slate-200 ${radius} 
                  shadow-sm hover:shadow-md transition-shadow`}
    >
      <div className="text-2xl mb-2">{data.emoji}</div>
      <div className="font-semibold text-slate-700">{data.title}</div>

      {/* 4 стороны */}
      <Port pos={Position.Top} />
      <Port pos={Position.Bottom} />
      <Port pos={Position.Left} />
      <Port pos={Position.Right} />
    </div>
  );
}
