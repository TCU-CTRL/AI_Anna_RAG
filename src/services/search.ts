import type { Env, SearchResult } from "../types";

const API_VERSION = "2024-07-01";

export async function search(
  env: Env,
  query: string,
  top: number = 5
): Promise<SearchResult[]> {
  const url = `${env.AZURE_SEARCH_ENDPOINT}/indexes/${env.AZURE_SEARCH_INDEX_NAME}/docs/search?api-version=${API_VERSION}`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "api-key": env.AZURE_SEARCH_API_KEY,
    },
    body: JSON.stringify({
      search: query,
      top,
      select: "id,title,content,source",
      queryType: "simple",
    }),
  });

  if (!response.ok) {
    console.error(
      `検索 API エラー: status=${response.status}, endpoint=${env.AZURE_SEARCH_ENDPOINT}`
    );
    throw new Error(`検索 API エラー (HTTP ${response.status})`);
  }

  const data = (await response.json()) as {
    value: Array<{
      id: string;
      title?: string;
      content?: string;
      source?: string;
      "@search.score"?: number;
    }>;
  };

  const results: SearchResult[] = (data.value ?? []).map((doc) => ({
    id: doc.id,
    title: doc.title ?? "",
    content: doc.content ?? "",
    source: doc.source ?? "",
    score: doc["@search.score"] ?? 0,
  }));

  results.sort((a, b) => b.score - a.score);
  return results;
}
