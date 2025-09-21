import type { ConnectionLineComponentProps } from "reactflow";
import { getSmoothStepPath } from "reactflow";

const EDGE_COLOR = "#38bdf8";
const INVALID_COLOR = "#f43f5e";

export default function SmartConnectionLine({
  fromX,
  fromY,
  toX,
  toY,
  fromPosition,
  toPosition,
  connectionLineStyle,
  connectionStatus,
}: ConnectionLineComponentProps) {
  const [path] = getSmoothStepPath({
    sourceX: fromX,
    sourceY: fromY,
    sourcePosition: fromPosition,
    targetX: toX,
    targetY: toY,
    targetPosition: toPosition,
    borderRadius: 32,
  });

  const isInvalid = connectionStatus === "invalid";
  const rawStrokeWidth = connectionLineStyle?.strokeWidth;
  const strokeWidth =
    typeof rawStrokeWidth === "number"
      ? rawStrokeWidth
      : typeof rawStrokeWidth === "string"
        ? Number.parseFloat(rawStrokeWidth) || 2
        : 2;
  const stroke = isInvalid
    ? INVALID_COLOR
    : connectionLineStyle?.stroke?.toString() ?? EDGE_COLOR;

  return (
    <g>
      <path
        className="react-flow__connection-line"
        d={path}
        stroke={stroke}
        strokeWidth={strokeWidth}
        strokeDasharray={isInvalid ? "6 3" : undefined}
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {isInvalid ? (
        <g transform={`translate(${toX}, ${toY})`}>
          <circle r={10} fill="white" stroke={INVALID_COLOR} strokeWidth={2} />
          <line
            x1={-5}
            y1={-5}
            x2={5}
            y2={5}
            stroke={INVALID_COLOR}
            strokeWidth={2}
            strokeLinecap="round"
          />
          <line
            x1={-5}
            y1={5}
            x2={5}
            y2={-5}
            stroke={INVALID_COLOR}
            strokeWidth={2}
            strokeLinecap="round"
          />
        </g>
      ) : null}
    </g>
  );
}
