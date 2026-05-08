import os
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    # CORS
    allowed_origins: str = Field(
        default=os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000"),
        description="Comma-separated list of allowed origins for CORS"
    )
    
    # Logging
    log_level: str = Field(
        default=os.environ.get("LOG_LEVEL", "INFO").upper(),
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(
        default=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "300")),
        description="Global local-development rate limit requests per minute per IP"
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

settings = Settings()
