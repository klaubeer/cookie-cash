from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Evolution API
    evolution_api_url: str
    evolution_api_key: str
    evolution_instance: str

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    # Google Sheets
    google_sheets_id: str
    google_credentials_json: str

    # WhatsApp
    grupo_whatsapp_id: str

    # App
    log_level: str = "INFO"
    confirmacao_ttl_segundos: int = 300
    confianca_min: float = 0.85


config = Configuracoes()
