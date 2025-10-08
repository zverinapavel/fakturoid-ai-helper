"""Configuration management for the invoice processor."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AIConfig(BaseModel):
    """AI model configuration."""
    provider: str = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.0
    max_tokens: int = 4096


class FakturoidConfig(BaseModel):
    """Fakturoid API configuration (OAuth 2.0 Client Credentials Flow)."""
    # For backward compatibility, email and api_key map to client_id and client_secret
    email: str = Field(default_factory=lambda: os.getenv("FAKTUROID_CLIENT_ID", os.getenv("FAKTUROID_EMAIL", "")))
    api_key: str = Field(default_factory=lambda: os.getenv("FAKTUROID_CLIENT_SECRET", os.getenv("FAKTUROID_API_KEY", "")))
    account_slug: str = Field(default_factory=lambda: os.getenv("FAKTUROID_ACCOUNT_SLUG", ""))
    base_url: str = "https://app.fakturoid.cz/api/v3"
    timeout: int = 30
    
    @property
    def client_id(self) -> str:
        """Alias for email field (OAuth 2.0 Client ID)."""
        return self.email
    
    @property
    def client_secret(self) -> str:
        """Alias for api_key field (OAuth 2.0 Client Secret)."""
        return self.api_key


class ProcessingConfig(BaseModel):
    """Processing configuration."""
    mode: str = Field(
        default_factory=lambda: os.getenv("PROCESSING_MODE", "manual")
    )
    auto_submit: bool = Field(
        default_factory=lambda: os.getenv("AUTO_SUBMIT", "false").lower() == "true"
    )
    batch_size: int = 10


class DirectoriesConfig(BaseModel):
    """Directory configuration."""
    project_root: Path = Path(__file__).parent.parent
    invoices: Path = Field(
        default_factory=lambda: Path(
            os.getenv("INVOICES_DIR", str(Path(__file__).parent.parent / "data" / "invoices"))
        ).resolve()  # Resolve to absolute path
    )
    processed: Path = Field(
        default_factory=lambda: Path(
            os.getenv("PROCESSED_DIR", str(Path(__file__).parent.parent / "data" / "processed"))
        ).resolve()  # Resolve to absolute path
    )


class ExtractionConfig(BaseModel):
    """Invoice extraction schema."""
    required_fields: List[str] = [
        "invoice_number",
        "issue_date",
        "supplier_name",
        "total_amount"
    ]
    optional_fields: List[str] = [
        "due_date",
        "variable_symbol",
        "supplier_address",
        "supplier_ico",
        "supplier_dic",
        "line_items",
        "tax_amount",
        "currency"
    ]


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Path = Path("logs/processor.log")


class Config(BaseModel):
    """Main configuration class."""
    ai: AIConfig = Field(default_factory=AIConfig)
    fakturoid: FakturoidConfig = Field(default_factory=FakturoidConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    directories: DirectoriesConfig = Field(default_factory=DirectoriesConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    @classmethod
    def load_from_yaml(cls, config_path: str = "config/settings.yaml") -> "Config":
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            # Return default configuration if file doesn't exist
            return cls()
        
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        
        return cls(**data)
    
    @property
    def anthropic_api_key(self) -> str:
        """Get Anthropic API key from environment."""
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        return key


# Global configuration instance
config = Config.load_from_yaml()

