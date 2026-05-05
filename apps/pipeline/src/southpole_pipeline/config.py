from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from zoneinfo import ZoneInfo


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    apify_token: str
    apify_actor_id: str
    apify_base_url: str
    apify_results_per_page: int
    apify_max_items: int
    apify_timeout_seconds: int
    apify_proxy_country_code: str
    apify_tiktok_comments_actor_id: str
    output_root: Path
    operator_state_root: Path
    build_tag: str
    timezone_name: str
    openai_api_key: str
    openai_model: str
    openai_analysis_model: str
    dm_brand_voice: str
    dm_default_language: str

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)


def load_settings() -> Settings:
    output_root = Path(os.getenv("OUTPUT_ROOT", "./outputs/runs"))
    return Settings(
        apify_token=os.getenv("APIFY_TOKEN", ""),
        apify_actor_id=os.getenv("APIFY_ACTOR_ID", "clockworks/tiktok-scraper"),
        apify_base_url=os.getenv("APIFY_BASE_URL", "https://api.apify.com/v2").rstrip("/"),
        apify_results_per_page=_env_int("APIFY_RESULTS_PER_PAGE", 25),
        apify_max_items=_env_int("APIFY_MAX_ITEMS", 200),
        apify_timeout_seconds=_env_int("APIFY_TIMEOUT_SECONDS", 600),
        apify_proxy_country_code=os.getenv("APIFY_PROXY_COUNTRY_CODE", "None"),
        apify_tiktok_comments_actor_id=os.getenv("APIFY_TIKTOK_COMMENTS_ACTOR_ID", ""),
        output_root=output_root,
        operator_state_root=Path(os.getenv("OPERATOR_STATE_ROOT", str(output_root.parent / "operator_state"))),
        build_tag=os.getenv("BUILD_TAG", "local-dev"),
        timezone_name=os.getenv("TZ", "Asia/Seoul"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        openai_analysis_model=os.getenv("OPENAI_ANALYSIS_MODEL", os.getenv("OPENAI_MODEL", "gpt-5-mini")),
        dm_brand_voice=os.getenv(
            "DM_BRAND_VOICE",
            "Southpole voice: respectful, clear, warm, and collaboration-focused.",
        ),
        dm_default_language=os.getenv("DM_DEFAULT_LANGUAGE", "auto"),
    )
