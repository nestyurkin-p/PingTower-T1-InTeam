
import {
  DEFAULT_PING_INTERVAL,
  buildWebsiteMetadata,
  type BaseNodeData,
  type BlockVariant,
} from "./nodes/types";


export type LibraryCategory = "Источники" | "Логика" | "Доставка";

export type LibraryNodeTemplate = {
  templateId: string;
  type: BlockVariant;
  category: LibraryCategory;
  data: BaseNodeData;
};

export const NODE_LIBRARY: LibraryNodeTemplate[] = [
  {
    templateId: "website-uptime",
    type: "website",
    category: "Источники",
    data: {

      title: "Пингер сайта",
      emoji: "🌐",
      description: "https://example.com",
      status: "idle",
      ping_interval: DEFAULT_PING_INTERVAL,
      metadata: buildWebsiteMetadata({
        title: "Пингер сайта",
        description: "https://example.com",
        ping_interval: DEFAULT_PING_INTERVAL,
      }),

    },
  },
  {
    templateId: "llm-autoreply",
    type: "llm",
    category: "Логика",
    data: {
      title: "LLM-ответчик",
      emoji: "🤖",
      description: "Генерирует персональные ответы клиентам",
      status: "idle",
      metadata: [
        { label: "Темп", value: "0.5" },
        { label: "Язык", value: "RU" },
      ],
    },
  },
  {
    templateId: "messenger-telegram",
    type: "messenger",
    category: "Доставка",
    data: {
      title: "Telegram бот",
      emoji: "📲",
      description: "Отправляет уведомления в Telegram",
      status: "idle",
      metadata: [
        { label: "Канал", value: "@pingtower" },
        { label: "Формат", value: "Markdown" },
      ],
    },
  },
  {
    templateId: "telegram-official-bot",
    type: "telegram",
    category: "Доставка",
    data: {
      title: "Telegram бот",
      emoji: "🤖",
      description: "@T1_InTeam_bot",
      status: "idle",
      metadata: [
        { label: "Тег", value: "@T1_InTeam_bot" },
        { label: "Статус", value: "Готов к приёму" },
      ],
    },
  },
];
