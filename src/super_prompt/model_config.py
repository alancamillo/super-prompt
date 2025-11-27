"""
Model configuration system for flexible multi-provider support.
Allows configuring models per complexity level and per tool.

Supports configuration via:
- Python code (ModelConfig, ModelProviderConfig classes)
- YAML file (load_config_from_yaml function)
"""
from typing import Optional, Dict
from pathlib import Path
import yaml
from pydantic import BaseModel, Field

class ModelConfig(BaseModel):
    """
    Configuration for a single LLM model/provider.
    
    Examples:
        # LM Studio local
        ModelConfig(
            name="qwen/qwen3-coder-30b",
            api_base="http://spark-0852.local:1234/v1",
            api_key=""
        )
        
        # OpenAI comercial
        ModelConfig(
            name="gpt-4o",
            api_base=None,  # Usa padrão da OpenAI
            api_key="sk-..."  # Ou usa OPENAI_API_KEY do .env
        )
    """
    name: str = Field(description="Model name (e.g., 'gpt-4o', 'qwen/qwen3-coder-30b')")
    api_base: Optional[str] = Field(default=None, description="API base URL. None uses provider default.")
    api_key: Optional[str] = Field(default=None, description="API key. None uses environment variables.")

class ModelProviderConfig(BaseModel):
    """
    Configuration for models at different complexity levels.
    Supports inheritance: if a tool doesn't have specific config, uses the complexity-level config.
    """
    simple: ModelConfig = Field(description="Model configuration for simple tasks/tools")
    complex: ModelConfig = Field(description="Model configuration for complex tasks/tools")
    tool_overrides: Optional[Dict[str, ModelConfig]] = Field(
        default=None,
        description="Tool-specific model overrides. Key is tool name, value is ModelConfig."
    )
    
    def get_model_for_tool(self, tool_name: str, tool_complexity: str) -> ModelConfig:
        """
        Gets the appropriate model configuration for a tool.
        
        Priority:
        1. Tool-specific override (if exists)
        2. Complexity-based config (simple/complex)
        
        Args:
            tool_name: Name of the tool
            tool_complexity: Complexity level of the tool ("simple" or "complex")
            
        Returns:
            ModelConfig to use for this tool
        """
        # Check for tool-specific override first
        if self.tool_overrides and tool_name in self.tool_overrides:
            return self.tool_overrides[tool_name]
        
        # Use complexity-based config
        if tool_complexity == "complex":
            return self.complex
        else:
            return self.simple


def load_config_from_yaml(config_path: str = "config.yaml") -> ModelProviderConfig:
    """
    Loads model configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file. Defaults to "config.yaml".
        
    Returns:
        ModelProviderConfig instance with the loaded configuration.
        
    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If the YAML structure is invalid.
        
    Example YAML structure:
        simple:
          name: "gpt-4o-mini"
          api_base: null
          api_key: null
        complex:
          name: "gpt-4o"
          api_base: null
          api_key: null
        tool_overrides:
          edit_lines:
            name: "gpt-4o"
            api_base: null
            api_key: null
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    
    if not config_data:
        raise ValueError(f"Configuration file is empty: {config_path}")
    
    # Validate required sections
    if "simple" not in config_data:
        raise ValueError("Configuration must have 'simple' section")
    if "complex" not in config_data:
        raise ValueError("Configuration must have 'complex' section")
    
    # Parse simple model config
    simple_config = ModelConfig(
        name=config_data["simple"]["name"],
        api_base=config_data["simple"].get("api_base"),
        api_key=config_data["simple"].get("api_key")
    )
    
    # Parse complex model config
    complex_config = ModelConfig(
        name=config_data["complex"]["name"],
        api_base=config_data["complex"].get("api_base"),
        api_key=config_data["complex"].get("api_key")
    )
    
    # Parse tool overrides if present
    tool_overrides = None
    if config_data.get("tool_overrides"):
        tool_overrides = {}
        for tool_name, tool_config in config_data["tool_overrides"].items():
            tool_overrides[tool_name] = ModelConfig(
                name=tool_config["name"],
                api_base=tool_config.get("api_base"),
                api_key=tool_config.get("api_key")
            )
    
    return ModelProviderConfig(
        simple=simple_config,
        complex=complex_config,
        tool_overrides=tool_overrides
    )


def try_load_config_from_yaml(config_path: str = "config.yaml") -> Optional[ModelProviderConfig]:
    """
    Attempts to load configuration from YAML, returns None if file doesn't exist.
    
    This is a convenience function that silently returns None if the config file
    is not found, making it useful for optional configuration.
    
    Args:
        config_path: Path to the YAML configuration file.
        
    Returns:
        ModelProviderConfig if file exists and is valid, None otherwise.
    """
    try:
        return load_config_from_yaml(config_path)
    except FileNotFoundError:
        return None

