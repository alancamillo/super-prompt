"""
Model configuration system for flexible multi-provider support.
Allows configuring models per complexity level and per tool.
"""
from typing import Optional, Dict
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

