import type { Env } from "./types";
import { search } from "./services/search";
import { generate } from "./services/ai";

const MAX_CONTENT_LENGTH = 2000;

const ERROR_MSG_SEARCH =
  "ごめんなさい、今ちょっと調べられないみたい...。少し待ってからもう一度聞いてね！";
const ERROR_MSG_GENERATE =
  "うーん、回答をまとめるのに失敗しちゃった...。もう一度試してみてね！";
const ERROR_MSG_UNEXPECTED =
  "ごめんなさい、何かうまくいかなかったみたい...。管理者に連絡してくれると助かるな";

export async function handleAnnaCommand(
  env: Env,
  interaction: {
    token: string;
    member?: { user?: { id: string } };
    user?: { id: string };
  },
  question: string
): Promise<void> {
  const userId =
    interaction.member?.user?.id ?? interaction.user?.id ?? "unknown";
  console.log(`質問を受信: user_id=${userId}`);

  const startTime = Date.now();

  try {
    const searchResults = await search(env, question);
    const answer = await generate(env, question, searchResults);

    let responseText = answer.content;
    if (answer.sources.length > 0) {
      responseText += `\n\n📚 参考: ${answer.sources.join("、")}`;
    }
    if (responseText.length > MAX_CONTENT_LENGTH) {
      responseText = responseText.slice(0, MAX_CONTENT_LENGTH - 3) + "...";
    }

    await editOriginalResponse(env, interaction.token, responseText);

    const elapsed = Date.now() - startTime;
    console.log(`回答完了(成功): user_id=${userId}, 処理時間=${elapsed}ms`);
  } catch (error) {
    const elapsed = Date.now() - startTime;
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error(
      `エラー: user_id=${userId}, 処理時間=${elapsed}ms, ${errorMsg}`
    );

    let userMessage = ERROR_MSG_UNEXPECTED;
    if (errorMsg.includes("検索")) {
      userMessage = ERROR_MSG_SEARCH;
    } else if (errorMsg.includes("回答生成")) {
      userMessage = ERROR_MSG_GENERATE;
    }

    await editOriginalResponse(env, interaction.token, userMessage);
  }
}

async function editOriginalResponse(
  env: Env,
  interactionToken: string,
  content: string
): Promise<void> {
  const url = `https://discord.com/api/v10/webhooks/${env.DISCORD_APP_ID}/${interactionToken}/messages/@original`;
  await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
}
