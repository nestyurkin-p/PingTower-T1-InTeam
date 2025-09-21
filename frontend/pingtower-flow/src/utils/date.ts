export function formatRelativeTime(timestamp?: number): string {
  if (!timestamp) return "никогда";

  const diff = Date.now() - timestamp;

  if (diff < 45_000) return "только что";

  const minutes = Math.round(diff / 60_000);
  if (minutes < 60) return `${minutes} мин назад`;

  const hours = Math.round(diff / 3_600_000);
  if (hours < 24) return `${hours} ч назад`;

  const days = Math.round(diff / 86_400_000);
  if (days < 7) return `${days} дн назад`;

  return new Date(timestamp).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatExactTime(timestamp?: number): string {
  if (!timestamp) return "—";

  return new Date(timestamp).toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
}
