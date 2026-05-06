from pathlib import Path

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    state_dir: Path = Field(default=Path("./data"), alias="DSP_DP_API_STATE_DIR")
    wren_ai_service_url: AnyHttpUrl = Field(default="http://localhost:5555", alias="WREN_AI_SERVICE_URL")
    wren_ibis_server_url: AnyHttpUrl = Field(default="http://localhost:8000", alias="WREN_IBIS_SERVER_URL")
    wren_manifest_registry_dir: Path = Field(default=Path("./data/manifests"), alias="WREN_MANIFEST_REGISTRY_DIR")


settings = Settings()
