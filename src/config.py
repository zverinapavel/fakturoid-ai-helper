"""Configuration management for the invoice processor."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project root - computed once at module import time
# This will be: /Users/pavelzverina/AiProjects/fakturoid
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def get_invoices_dir() -> Path:
    """Get invoices directory as absolute path (from YAML or default)."""
    # Use default - YAML values will override this via Pydantic
    return PROJECT_ROOT / "data" / "invoices"


def get_processed_dir() -> Path:
    """Get processed directory as absolute path (from YAML or default)."""
    # Use default - YAML values will override this via Pydantic
    return PROJECT_ROOT / "data" / "processed"


class AIConfig(BaseModel):
    """AI model configuration."""
    provider: str = Field(
        default_factory=lambda: os.getenv("AI_PROVIDER", "anthropic")
    )
    model: str = Field(
        default_factory=lambda: os.getenv("AI_MODEL", "claude-sonnet-4-5-20250929")
    )
    temperature: float = 0.0
    max_tokens: int = 4096
    
    # Provider-specific settings
    ollama_base_url: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )


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
    project_root: Path = Field(default_factory=lambda: PROJECT_ROOT)
    invoices: Path = Field(default_factory=get_invoices_dir)
    processed: Path = Field(default_factory=get_processed_dir)
    
    @model_validator(mode='after')
    def make_paths_absolute(self):
        """Ensure all paths are absolute, relative to project root.
        
        This handles paths from YAML config that come as strings.
        """
        # Make invoices absolute if it's relative
        if not self.invoices.is_absolute():
            self.invoices = PROJECT_ROOT / self.invoices
        
        # Make processed absolute if it's relative
        if not self.processed.is_absolute():
            self.processed = PROJECT_ROOT / self.processed
        
        return self


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
    
    @property
    def openai_api_key(self) -> str:
        """Get OpenAI API key from environment."""
        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        return key
    
    @property
    def deepseek_api_key(self) -> str:
        """Get DeepSeek API key from environment."""
        key = os.getenv("DEEPSEEK_API_KEY", "")
        if not key:
            raise ValueError("DEEPSEEK_API_KEY not set in environment")
        return key
    
    @property
    def groq_api_key(self) -> str:
        """Get Groq API key from environment."""
        key = os.getenv("GROQ_API_KEY", "")
        if not key:
            raise ValueError("GROQ_API_KEY not set in environment")
        return key
    
    def get_api_key(self, provider: str = None) -> str:
        """Get API key for the configured or specified provider."""
        provider = provider or self.ai.provider
        
        if provider == "anthropic":
            return self.anthropic_api_key
        elif provider == "openai":
            return self.openai_api_key
        elif provider == "deepseek":
            return self.deepseek_api_key
        elif provider == "groq":
            return self.groq_api_key
        elif provider == "ollama":
            return ""  # Ollama doesn't require API key for local
        else:
            raise ValueError(f"Unknown provider: {provider}")


# Global configuration instance
config = Config.load_from_yaml()

