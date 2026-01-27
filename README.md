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
RECALL_LINES_DEFAULT=50
RECALL_PICK_DEFAULT=10
AUTO_RECALL_LINES=40
AUTO_RECALL_PICK=8
AUTO_RECALL_KEYWORDS=前に,前回,以前,昔,過去,覚えて,覚えてる,記憶,ログ,履歴
BOOTSTRAP_LOG_LINES=500
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
- `@bot /recall 50 10` のように過去ログを読み出すと、末尾50行から10行を抜粋して文脈に追加します。
- 自動リコールはキーワード検出で末尾ログを読み込みます。
- `@bot しゆいって呼称してほしい` のように呼び方を覚えます。指定がなければディスプレイネームを使います。
- 呼称に「しゆい」は特別ユーザー以外は設定できません。
- `/help` か `@bot help` で使い方を表示します。
