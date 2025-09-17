export function canConnect(source?: string, target?: string) {
  if (!source || !target) return false;
  if (source === "website" && (target === "llm" || target === "messenger")) return true;
  if (source === "llm" && target === "messenger") return true;
  return false;
}
