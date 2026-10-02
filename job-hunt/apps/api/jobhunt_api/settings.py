from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "job-hunt-api"
    environment: str = "local"
    database_url: str = "postgresql://jobhunt:jobhunt@127.0.0.1:5432/jobhunt"
    auth_mode: str = "test"
    clerk_issuer: str = ""
    clerk_jwks_url: str = ""
    test_jwt_secret: str = "jobhunt-test-secret-32b-minimum-key!"
    token_encryption_key: str = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    token_encryption_key_previous: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = ""
    feature_us_market: bool = False
    feature_live_ats_http: bool = False
    feature_document_drafts: bool = True
    feature_gmail_alerts: bool = True
    feature_browser_capture: bool = True
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "candidate-artifacts"
    gmail_allowed_labels: str = "JobAlerts,Jobs"
    gmail_max_messages_per_ingest: int = 25
    gmail_redirect_allowlist: str = ""
    oauth_state_secret: str = ""
    feature_external_gmail: bool = False
    allow_gmail_oauth_dev: bool = False
    uat_signoff_secret: str = ""
    uat_admin_user_ids: str = ""
    uat_signoff_ttl_days: int = 90
    worker_internal_url: str = "http://127.0.0.1:8001"
    strong_match_threshold: float = 50.0
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"
    rate_limit_per_minute: int = 120


settings = Settings()
