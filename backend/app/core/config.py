from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SIAPEC IDIARN PNIB"
    database_url: str = "sqlite:///./siapec_idiarn.db"
    pnib_etapa: int = 2
    cors_origins: str = "http://localhost:5173"
    # Índices SIAPEC-like (demo; admin poderá ajustar depois)
    indice_paricao: float = 0.35  # máx. nascimentos / fêmeas adultas (25+)
    indice_mortalidade_mes: float = 0.02  # máx. mortes no mês / saldo total

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
