import {
  InteractionType,
  InteractionResponseType,
  verifyKey,
} from "discord-interactions";
import type { Env } from "./types";
import { handleAnnaCommand } from "./commands";

export default {
  async fetch(
    request: Request,
    env: Env,
    ctx: ExecutionContext
  ): Promise<Response> {
    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    // 署名検証
    const signature = request.headers.get("x-signature-ed25519");
    const timestamp = request.headers.get("x-signature-timestamp");
    const body = await request.text();

    if (!signature || !timestamp) {
      return new Response("Bad Request", { status: 400 });
    }

    const isValid = await verifyKey(
      body,
      signature,
      timestamp,
      env.DISCORD_PUBLIC_KEY
    );
    if (!isValid) {
      return new Response("Invalid signature", { status: 401 });
    }

    const interaction = JSON.parse(body);

    // PING/PONG (Discord のエンドポイント検証)
    if (interaction.type === InteractionType.PING) {
      return Response.json({ type: InteractionResponseType.PONG });
    }

    // スラッシュコマンド
    if (interaction.type === InteractionType.APPLICATION_COMMAND) {
      if (interaction.data.name === "anna") {
        const question =
          interaction.data.options?.find(
            (opt: { name: string; value: string }) => opt.name === "question"
          )?.value ?? "";

        if (!question) {
          return Response.json({
            type: InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
            data: {
              content:
                "質問を入れてね！ `/anna 質問内容` で聞いてくれると嬉しいな",
            },
          });
        }

        // Deferred Response を即座に返し、裏で処理
        ctx.waitUntil(handleAnnaCommand(env, interaction, question));

        return Response.json({
          type: InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE,
        });
      }
    }

    return Response.json({ error: "Unknown command" }, { status: 400 });
  },
};
