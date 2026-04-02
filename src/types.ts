export interface Env {
  DISCORD_APP_ID: string;
  DISCORD_PUBLIC_KEY: string;
  DISCORD_BOT_TOKEN: string;
  AZURE_SEARCH_ENDPOINT: string;
  AZURE_SEARCH_API_KEY: string;
  AZURE_SEARCH_INDEX_NAME: string;
  GEMINI_API_KEY: string;
}

export interface SearchResult {
  id: string;
  title: string;
  content: string;
  source: string;
  score: number;
}

export interface GeneratedAnswer {
  content: string;
  sources: string[];
  hasSufficientContext: boolean;
}
