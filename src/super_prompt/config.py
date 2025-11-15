"""
Configuration for the Modern AI Agent using Pydantic.
"""
from typing import Optional, List
from pydantic import BaseModel, Field

class AgentConfig(BaseModel):
    """
    Configuration settings for the ModernAIAgent, validated by Pydantic.
    """
    workspace: str = Field(default=".", description="The working directory for the agent.")
    model: Optional[str] = Field(default=None, description="Fixed OpenAI model to use. Overrides multi-model settings.")
    simple_model: str = Field(default="gpt-4o-mini", description="Model for simple tasks like reading or listing files.")
    complex_model: str = Field(default="gpt-4o", description="Model for complex tasks like planning and validation.")
    use_multi_model: bool = Field(default=False, description="Whether to use different models based on tool complexity.")
    max_iterations: int = Field(default=30, description="Maximum number of tool-call iterations per task.")
    verbose: bool = Field(default=True, description="Enable detailed logging to the console.")
    log_file: Optional[str] = Field(default="logs/agent_session.log", description="Path to save the execution log.")
    max_history_tasks: int = Field(default=3, description="Number of recent full task conversations to keep in memory.")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore" # Ignore extra fields from .env
