import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from functools import lru_cache


class DatabaseConfig(BaseModel):
    url: str
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20


class ModelsConfig(BaseModel):
    """Model configuration"""
    default_model: str = "claude-sonnet-4"
    timeout: int = 30


class EvaluatorsConfig(BaseModel):
    """Evaluator configuration"""
    enabled: list[str] = ["latency", "toxicity", "factuality"]


class CybersecurityConfig(BaseModel):
    """Cybersecurity-specific configuration"""
    ioc_types: list[str] = ["ip", "domain", "url", "hash", "email"]


class Config(BaseModel):
    environment: str = "dev"
    database: DatabaseConfig
    models: Dict[str, Any] = {}
    evaluators: Dict[str, Any] = {}
    cybersecurity: Dict[str, Any] = {}
    
    # Convenience property for backward compatibility
    @property
    def database_url(self) -> str:
        """Backward compatibility: access database URL directly"""
        return self.database.url
    
    @property
    def database_echo(self) -> bool:
        return self.database.echo
    
    @property
    def database_pool_size(self) -> int:
        return self.database.pool_size
    
    @property
    def database_max_overflow(self) -> int:
        return self.database.max_overflow


@lru_cache()
def get_config(env: Optional[str] = None) -> Config:
    """
    Load configuration from YAML
    
    Args:
        env: Environment name (dev, test, prod). If None, uses APP_ENV or defaults to 'dev'
    """
    if env is None:
        env = os.getenv("APP_ENV", "dev")
    
    config_path = Path(__file__).parent.parent.parent / "configs" / f"{env}.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)
    
    # Ensure environment is set
    if "environment" not in config_dict:
        config_dict["environment"] = env
    
    return Config(**config_dict)


# Convenience functions
def get_database_url(env: Optional[str] = None) -> str:
    """Get database URL for specified environment"""
    return get_config(env).database.url


def get_database_config(env: Optional[str] = None) -> DatabaseConfig:
    """Get full database configuration"""
    return get_config(env).database