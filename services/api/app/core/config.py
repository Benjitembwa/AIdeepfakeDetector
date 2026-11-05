from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="PRISME_",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Prisme API"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: SecretStr
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: str = "https://a-ideepfake-detector.vercel.app,http://localhost:3000,http://127.0.0.1:3000"
    max_upload_bytes: int = 10 * 1024 * 1024
    verification_candidate_limit: int = 1000
    sightengine_api_user: SecretStr | None = None
    sightengine_api_secret: SecretStr | None = None
    sightengine_api_url: str = "https://api.sightengine.com/1.0/check.json"
    sightengine_timeout_seconds: float = 20.0
    pinata_jwt: SecretStr | None = None
    pinata_gateway: str | None = None
    pinata_upload_url: str = "https://uploads.pinata.cloud/v3/files"
    pinata_api_url: str = "https://api.pinata.cloud/v3"
    pinata_timeout_seconds: float = 60.0
    base_rpc_url: str = "https://sepolia.base.org"
    base_chain_id: int = 84532
    base_explorer_url: str = "https://sepolia.basescan.org"
    registry_contract_address: str = "0x0000000000000000000000000000000000000000"
    blockchain_receipt_timeout_seconds: float = 90.0
    c2pa_sign_cert_path: Path = ENV_FILE.parent / "tests/fixtures/c2pa/es256_certs.pem"
    c2pa_private_key_path: Path = ENV_FILE.parent / "tests/fixtures/c2pa/es256_private.key"

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters")
        return value

    @field_validator("c2pa_sign_cert_path", "c2pa_private_key_path", mode="before")
    @classmethod
    def resolve_c2pa_path(cls, value: str | Path) -> Path:
        path = Path(value)
        return path if path.is_absolute() else ENV_FILE.parent / path

    @property
    def sqlalchemy_database_url(self) -> str:
        value = self.database_url.get_secret_value()
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def pinata_gateway_base_url(self) -> str | None:
        if not self.pinata_gateway:
            return None
        gateway = self.pinata_gateway.strip().rstrip("/")
        return gateway if gateway.startswith("https://") else f"https://{gateway}"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
