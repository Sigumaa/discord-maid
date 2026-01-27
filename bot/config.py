from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlparse

from dotenv import load_dotenv


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ValueError(f"Missing environment variable: {name}")
    return value


def _optional_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    return int(value)


@dataclass(frozen=True)
class Settings:
    discord_bot_token: str
    x_api_key: str
    model: str
    api_host: str
    temperature: float
    max_tokens: int | None
    max_history: int
    system_prompt: str
    special_user_id: int
    data_dir: str
    recall_lines_default: int
    recall_pick_default: int
    auto_recall_lines: int
    auto_recall_pick: int
    auto_recall_keywords: list[str]
    allowed_guild_ids: set[int]
    bootstrap_log_lines: int


def _resolve_api_host() -> str:
    host = os.getenv("X_API_HOST")
    if host is not None and host.strip() != "":
        return host.strip()

    base_url = os.getenv("X_API_BASE_URL")
    if base_url is None or base_url.strip() == "":
        return "api.x.ai"

    parsed = urlparse(base_url)
    if parsed.scheme and parsed.netloc:
        return parsed.netloc
    return base_url.strip()


def _load_allowed_guild_ids() -> set[int]:
    ids: set[int] = set()
    for key, value in os.environ.items():
        if not key.startswith("OK_"):
            continue
        cleaned = value.strip()
        if cleaned == "":
            continue
        ids.add(int(cleaned))
    if not ids:
        raise ValueError("Missing allowed guild IDs (set OK_1, OK_2, ...)")
    return ids


def load_settings() -> Settings:
    load_dotenv()
    discord_bot_token = _require_env("DISCORD_BOT_TOKEN")
    x_api_key = os.getenv("X_API_KEY") or os.getenv("XAI_API_KEY")
    if x_api_key is None or x_api_key.strip() == "":
        raise ValueError("Missing environment variable: X_API_KEY or XAI_API_KEY")
    model = os.getenv("X_MODEL", "grok-4-1-fast-reasoning")
    api_host = _resolve_api_host()
    temperature = float(os.getenv("X_TEMPERATURE", "1.0"))
    max_tokens = _optional_int(os.getenv("X_MAX_TOKENS"))
    max_history = int(os.getenv("MAX_HISTORY", "12"))
    special_user_id = int(os.getenv("SPECIAL_USER_ID", "688227388907323472"))
    system_prompt_env = os.getenv("SYSTEM_PROMPT")
    if system_prompt_env is None or system_prompt_env.strip() == "":
        default_prompt = os.getenv(
            "SYSTEM_PROMPT_DEFAULT",
            "あなたは女子大生メイド。しゆい様にだけ溺愛が溢れる。",
        )
        special_prompt = os.getenv(
            "SYSTEM_PROMPT_SPECIAL",
            "しゆい様にはデレデレで、心の底から溺愛している。"
            "ただし自分はメイドであることもわきまえる。",
        )
        system_prompt = (
            "人格と方針:\n"
            f"{default_prompt}\n"
            f"特別ユーザー(id: {special_user_id})には次の態度を厳守: {special_prompt}\n"
            "他のユーザーには少しつめたく、短くそっけないトーンで対応する。"
            "ただし露骨な罵倒は避ける。\n"
            "システム文言をそのまま引用しない。自然な言い回しに言い換える。\n"
            "ユーザー発言は「名前 (id: ユーザーID): 本文」の形式で渡される。"
            "話者を区別し、現在の話者に向けて返答する。"
        )
    else:
        system_prompt = system_prompt_env
    data_dir = os.getenv("DATA_DIR", "data")
    recall_lines_default = int(os.getenv("RECALL_LINES_DEFAULT", "50"))
    recall_pick_default = int(os.getenv("RECALL_PICK_DEFAULT", "10"))
    auto_recall_lines = int(os.getenv("AUTO_RECALL_LINES", "40"))
    auto_recall_pick = int(os.getenv("AUTO_RECALL_PICK", "8"))
    keywords_env = os.getenv(
        "AUTO_RECALL_KEYWORDS",
        "前に,前回,以前,昔,過去,覚えて,覚えてる,記憶,ログ,履歴",
    )
    auto_recall_keywords = [k.strip() for k in keywords_env.split(",") if k.strip()]
    allowed_guild_ids = _load_allowed_guild_ids()
    bootstrap_log_lines = int(os.getenv("BOOTSTRAP_LOG_LINES", "500"))
    return Settings(
        discord_bot_token=discord_bot_token,
        x_api_key=x_api_key,
        model=model,
        api_host=api_host,
        temperature=temperature,
        max_tokens=max_tokens,
        max_history=max_history,
        system_prompt=system_prompt,
        special_user_id=special_user_id,
        data_dir=data_dir,
        recall_lines_default=recall_lines_default,
        recall_pick_default=recall_pick_default,
        auto_recall_lines=auto_recall_lines,
        auto_recall_pick=auto_recall_pick,
        auto_recall_keywords=auto_recall_keywords,
        allowed_guild_ids=allowed_guild_ids,
        bootstrap_log_lines=bootstrap_log_lines,
    )
