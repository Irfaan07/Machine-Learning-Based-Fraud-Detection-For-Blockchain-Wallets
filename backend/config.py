import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./fraud_wallet_v2.db")
    ETHERSCAN_API_KEY: str | None = os.getenv("ETHERSCAN_API_KEY")
    BLOCKCYPHER_API_TOKEN: str | None = os.getenv("BLOCKCYPHER_API_TOKEN")

    API_TIMEOUT_SECONDS: int = int(os.getenv("API_TIMEOUT_SECONDS", "15"))
    MAX_TX_FETCH: int = int(os.getenv("MAX_TX_FETCH", "200"))

    BACKEND_CORS_ORIGINS: str = os.getenv("BACKEND_CORS_ORIGINS", "*")


settings = Settings()

