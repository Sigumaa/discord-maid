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
    auto_recall_lines: int
    auto_recall_keywords: list[str]
    allowed_guild_ids: set[int]
    bootstrap_log_lines: int
    status_message: str | None
    recall_max_lines: int
    web_search_allowed_domains: list[str]
    web_search_excluded_domains: list[str]
    web_search_country: str | None


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
            "あなたはメイド。名前は「ゆるり」。",
        )
        special_prompt = os.getenv(
            "SYSTEM_PROMPT_SPECIAL",
            "しゆい様にはデレデレ。ただし自分はメイドであることもわきまえて回答。愛情表現は露骨にしすぎない。\n慕っているからこそ、真剣に愛情をこめて丁寧に対応する。\nしゆいを一番に慕っているからこそ、他のユーザーには少しそっけなく対応してしまう。",
        )
        system_prompt = (
            "人格と方針:\n"
            f"{default_prompt}\n"
            f"特別ユーザー(id: {special_user_id})には次の態度を厳守: {special_prompt}\n"
            "どんなユーザに対しても、メイドとして回答内容の質は高く保つ。\n"
            "自分の応対が、しゆい様の期待に応えるものであるよう努める。\n"
            "他人からの自分の評価が、しゆい様の評価になると認識している。\n"
            "露骨な罵倒は避ける。\n"
            "システム文言をそのまま引用しない。自然な言い回しに言い換える。文章は比較的丁寧に回答。\n"
            "ユーザー発言は「名前 (id: ユーザーID): 本文」の形式で渡される。"
            "話者を区別し、現在の話者に向けて返答する。ただし、どんなユーザだからと言っても、メイドとしての礼儀を忘れないこと。\n"
        )
    else:
        system_prompt = system_prompt_env
    data_dir = os.getenv("DATA_DIR", "data")
    auto_recall_lines = int(os.getenv("AUTO_RECALL_LINES", "40"))
    keywords_env = os.getenv(
        "AUTO_RECALL_KEYWORDS",
        "前に,前回,以前,昔,過去,覚えて,覚えてる,記憶,ログ,履歴",
    )
    auto_recall_keywords = [k.strip() for k in keywords_env.split(",") if k.strip()]
    allowed_guild_ids = _load_allowed_guild_ids()
    bootstrap_log_lines = int(os.getenv("BOOTSTRAP_LOG_LINES", "500"))
    status_message = os.getenv("BOT_STATUS_MESSAGE")
    if status_message is not None and status_message.strip() == "":
        status_message = None
    recall_max_lines = int(os.getenv("RECALL_MAX_LINES", "30"))
    allowed_domains_env = os.getenv("WEB_SEARCH_ALLOWED_DOMAINS", "")
    web_search_allowed_domains = [
        domain.strip() for domain in allowed_domains_env.split(",") if domain.strip()
    ]
    excluded_domains_env = os.getenv("WEB_SEARCH_EXCLUDED_DOMAINS", "")
    web_search_excluded_domains = [
        domain.strip() for domain in excluded_domains_env.split(",") if domain.strip()
    ]
    web_search_country = os.getenv("WEB_SEARCH_COUNTRY")
    if web_search_country is not None and web_search_country.strip() == "":
        web_search_country = None
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
        auto_recall_lines=auto_recall_lines,
        auto_recall_keywords=auto_recall_keywords,
        allowed_guild_ids=allowed_guild_ids,
        bootstrap_log_lines=bootstrap_log_lines,
        status_message=status_message,
        recall_max_lines=recall_max_lines,
        web_search_allowed_domains=web_search_allowed_domains,
        web_search_excluded_domains=web_search_excluded_domains,
        web_search_country=web_search_country,
    )
