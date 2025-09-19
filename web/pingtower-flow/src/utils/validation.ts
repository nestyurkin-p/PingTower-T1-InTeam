export function canConnect(sourceType?: string, targetType?: string): boolean {
  if (!sourceType || !targetType) return false;

  if (sourceType === "website" && (targetType === "llm" || targetType === "messenger")) return true;
  if (sourceType === "llm" && targetType === "messenger") return true;

  return false;
}
