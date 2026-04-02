/**
 * Discord にスラッシュコマンドを登録するスクリプト。
 *
 * 使い方:
 *   DISCORD_APP_ID=... DISCORD_BOT_TOKEN=... npm run register
 */

const ANNA_COMMAND = {
  name: "anna",
  description: "anna に質問する",
  options: [
    {
      type: 3, // STRING
      name: "question",
      description: "質問内容",
      required: true,
    },
  ],
};

async function main() {
  const appId = process.env.DISCORD_APP_ID;
  const botToken = process.env.DISCORD_BOT_TOKEN;

  if (!appId || !botToken) {
    console.error(
      "DISCORD_APP_ID と DISCORD_BOT_TOKEN を環境変数に設定してください"
    );
    process.exit(1);
  }

  const url = `https://discord.com/api/v10/applications/${appId}/commands`;

  console.log("スラッシュコマンドを登録中...");

  const response = await fetch(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bot ${botToken}`,
    },
    body: JSON.stringify([ANNA_COMMAND]),
  });

  if (!response.ok) {
    const error = await response.text();
    console.error(`登録失敗: ${response.status} ${error}`);
    process.exit(1);
  }

  const data = await response.json();
  console.log("登録成功:", JSON.stringify(data, null, 2));
}

main();
