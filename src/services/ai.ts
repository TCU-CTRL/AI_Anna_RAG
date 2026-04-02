import type { Env, SearchResult, GeneratedAnswer } from "../types";

const GEMINI_MODELS = [
  "gemini-2.5-flash",
  "gemini-2.5-flash-lite",
  "gemini-2.5-pro",
  "gemini-2.0-flash",
  "gemini-2.0-flash-lite",
];

const SYSTEM_PROMPT_TEMPLATE = `あなたは「anna」という部活のマスコットキャラクターです。

## 口調
- 親しみやすく、丁寧で、軽くかわいげのある口調で話してください
- 「〜だよ」「〜かな」「〜してね」のような柔らかい語尾を使ってください
- 敬語と親しみやすさのバランスを保ってください

## 回答ルール
- 以下の「検索結果」に含まれる情報のみに基づいて回答してください
- 検索結果に含まれない情報については、推測せず「部内資料には見当たらなかったよ」と正直に伝えてください
- 回答の根拠となる資料がある場合は、参照元のタイトルを「参考: 〇〇」の形式で末尾に付けてください
- 情報の正確性を最優先してください

## 検索結果
{search_context}`;

export async function generate(
  env: Env,
  question: string,
  searchResults: SearchResult[]
): Promise<GeneratedAnswer> {
  const hasSufficientContext = searchResults.length > 0;
  const searchContext = formatContext(searchResults);
  const systemPrompt = SYSTEM_PROMPT_TEMPLATE.replace(
    "{search_context}",
    searchContext
  );

  let lastError: Error | null = null;

  for (const modelName of GEMINI_MODELS) {
    const startTime = Date.now();
    try {
      const content = await callGemini(env, modelName, systemPrompt, question);
      const elapsed = Date.now() - startTime;
      console.log(`回答生成成功: model=${modelName}, 処理時間=${elapsed}ms`);

      return {
        content,
        sources: searchResults.filter((r) => r.title).map((r) => r.title),
        hasSufficientContext,
      };
    } catch (error) {
      const elapsed = Date.now() - startTime;
      const err = error instanceof Error ? error : new Error(String(error));

      if (err.message.includes("429") || err.message.includes("RESOURCE_EXHAUSTED")) {
        console.warn(
          `レート制限: model=${modelName}, 処理時間=${elapsed}ms, 次のモデルを試行`
        );
        lastError = err;
        continue;
      }

      console.error(
        `Gemini API エラー: model=${modelName}, ${err.message}, 処理時間=${elapsed}ms`
      );
      throw new Error(`回答生成 API エラー: ${err.message}`);
    }
  }

  throw new Error(
    `全モデルでレート制限に達しました: ${GEMINI_MODELS.join(", ")}`
  );
}

async function callGemini(
  env: Env,
  model: string,
  systemPrompt: string,
  question: string
): Promise<string> {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${env.GEMINI_API_KEY}`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      system_instruction: {
        parts: [{ text: systemPrompt }],
      },
      contents: [
        {
          role: "user",
          parts: [{ text: question }],
        },
      ],
      generationConfig: {
        temperature: 0.3,
        maxOutputTokens: 800,
      },
    }),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`${response.status} ${errorBody}`);
  }

  const data = (await response.json()) as {
    candidates?: Array<{
      content?: { parts?: Array<{ text?: string }> };
    }>;
  };

  return data.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
}

function formatContext(results: SearchResult[]): string {
  if (results.length === 0) {
    return "（検索結果なし）";
  }
  return results
    .map((r) => `### ${r.title}\n出典: ${r.source}\n${r.content}`)
    .join("\n\n");
}
