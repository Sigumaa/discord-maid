# Grok Discord Bot

Grok (grok-4-1-fast-reasoning) を使うメンション応答の Discord Bot です。

## セットアップ

```bash
uv venv .venv
uv sync
```

`.env` に以下が入っている前提です。（`XAI_API_KEY` でも可）

```
DISCORD_BOT_TOKEN=...
X_API_KEY=...
```

任意の設定:

```
X_MODEL=grok-4-1-fast-reasoning
X_API_HOST=api.x.ai
X_TEMPERATURE=0.2
X_MAX_TOKENS=512
MAX_HISTORY=8
SYSTEM_PROMPT=（1本化したシステムプロンプト）
SYSTEM_PROMPT_DEFAULT=（未指定時のベース、任意）
SYSTEM_PROMPT_SPECIAL=（未指定時の特別ユーザー文言、任意）
SPECIAL_USER_ID=
DATA_DIR=data
AUTO_RECALL_LINES=40
AUTO_RECALL_KEYWORDS=前に,前回,以前,昔,過去,覚えて,覚えてる,記憶,ログ,履歴
BOOTSTRAP_LOG_LINES=500
BOT_STATUS_MESSAGE=メンションしてhelpって打ってください♡
RECALL_MAX_LINES=30
WEB_SEARCH_ALLOWED_DOMAINS=
WEB_SEARCH_EXCLUDED_DOMAINS=
WEB_SEARCH_COUNTRY=JP
ANNOUNCE_GUILD_ID=683939861539192860
ANNOUNCE_CHANNEL_ID=929745598637309973
ANNOUNCE_START_MESSAGE=起床しました。
ANNOUNCE_STOP_MESSAGE=私はもう寝ますわ、、、
OK_1=
OK_2=
LOG_LEVEL=DEBUG
```

## 実行

```bash
uv run bot
```

## 使い方

- サーバー上でボットにメンションすると応答します（許可サーバーのみ）。
- DM には反応しません。
- 会話メモリはチャンネル/スレッド単位で共有されます。
- 再起動時は `BOOTSTRAP_LOG_LINES` 行ぶんのログから直近メモリを復元します。
- `@bot /recall 10` のように過去ログを読み出すと、末尾10行を文脈に追加します。
- `@bot /clear` でこのチャンネルの会話履歴（メモリ）をクリアします（ログは保持）。
- `@bot /fresh 質問内容` で履歴クリア後に同じ内容を即送信します。
- Web/X/コード実行ツールは常時有効です（`/web` `/x` `/code` は明示指示用）。
- 起動/終了通知は LLM が毎回生成します（失敗時は ANNOUNCE_* をフォールバック）。
- 自動リコールはキーワード検出で末尾ログを読み込みます。
- `@bot しゆいって呼称してほしい` のように呼び方を覚えます。指定がなければディスプレイネームを使います。
- 呼称に「しゆい」は特別ユーザー以外は設定できません。
- `/help` か `@bot help` で使い方を表示します。
- Web検索は `@bot /web 〇〇` で有効になります（許可ドメインは env で制限可能）。
- X検索は `@bot /x 〇〇` で有効になります。
- コード実行は `@bot /code 〇〇` で有効になります。
- 検索時は出典（ドメイン一覧）と inline citations を返します。
- 画像はメッセージに添付すると読み取ります（最大2枚、PNG/JPG、10MiB以下）。
