"""
Configuration for the Modern AI Agent using Pydantic.

Supports configuration via:
- Python code (AgentConfig class)
- YAML file (config.yaml) - automatically loaded if present
"""
from typing import Optional, List, Dict, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from .model_config import ModelConfig, ModelProviderConfig, try_load_config_from_yaml

class AgentConfig(BaseModel):
    """
    Configuration settings for the ModernAIAgent, validated by Pydantic.
    
    Uses LiteLLM SDK to support 100+ LLM providers (OpenAI, LM Studio, Ollama, Anthropic, etc.)
    
    You can configure these settings via:
    1. Direct instantiation: AgentConfig(max_iterations=50)
    2. Environment variables: MAX_ITERATIONS=50 in .env file
    3. Per-task override: execute_task(task, max_iterations=50)
    
    Examples:
        # OpenAI (default)
        config = AgentConfig(simple_model="gpt-4o-mini")
        
        # LM Studio local
        config = AgentConfig(
            simple_model="lm_studio/qwen2.5-7b-instruct",
            api_base="http://localhost:1234/v1"
        )
        
        # Ollama
        config = AgentConfig(
            simple_model="ollama/llama3",
            api_base="http://localhost:11434"
        )
    """
    workspace: str = Field(default=".", description="The working directory for the agent.")
    
    # YAML configuration file
    config_file: Optional[str] = Field(
        default=None, 
        description="Path to YAML config file. If set, loads model configuration from this file."
    )
    
    # Legacy configuration (mantido para compatibilidade)
    model: Optional[str] = Field(default=None, description="[LEGACY] Fixed model to use. Overrides multi-model settings. Use model_provider_config for new flexible system.")
    simple_model: Optional[str] = Field(default=None, description="[LEGACY] Model for simple tasks. Use model_provider_config for new flexible system.")
    complex_model: Optional[str] = Field(default=None, description="[LEGACY] Model for complex tasks. Use model_provider_config for new flexible system.")
    use_multi_model: bool = Field(default=False, description="Whether to use different models based on tool complexity.")
    api_base: Optional[str] = Field(default=None, description="[LEGACY] API base URL for custom providers. Use model_provider_config for per-model configuration.")
    api_key: Optional[str] = Field(default=None, description="[LEGACY] API key for the provider. Use model_provider_config for per-model configuration.")
    
    # New flexible configuration system
    model_provider_config: Optional[ModelProviderConfig] = Field(
        default=None,
        description="""Flexible model configuration supporting multiple providers.
        
        Example with LM Studio (local) for simple tasks and OpenAI (commercial) for complex:
        ModelProviderConfig(
            simple=ModelConfig(
                name="qwen/qwen3-coder-30b",
                api_base="http://spark-0852.local:1234/v1",
                api_key=""
            ),
            complex=ModelConfig(
                name="gpt-4o",
                api_base=None,  # Uses OpenAI default
                api_key=None    # Uses OPENAI_API_KEY from .env
            ),
            tool_overrides={
                "edit_lines": ModelConfig(
                    name="gpt-4o",
                    api_base=None,
                    api_key=None
                )
            }
        )
        """
    )
    max_iterations: int = Field(
        default=30, 
        ge=1, 
        le=1000,
        description="Maximum number of tool-call iterations per task. Range: 1-1000. Can be overridden per task."
    )
    verbose: bool = Field(default=True, description="Enable detailed logging to the console.")
    log_file: Optional[str] = Field(default="logs/agent_session.log", description="Path to save the execution log.")
    max_history_tasks: int = Field(default=3, description="Number of recent full task conversations to keep in memory.")

    @field_validator('max_iterations')
    @classmethod
    def validate_max_iterations(cls, v):
        """Valida que max_iterations está em um range razoável."""
        if v < 1:
            raise ValueError("max_iterations deve ser pelo menos 1")
        if v > 1000:
            raise ValueError("max_iterations não deve exceder 1000 para evitar loops infinitos")
        return v
    
    @model_validator(mode='after')
    def setup_model_config(self):
        """
        Configura model_provider_config com a seguinte prioridade:
        1. model_provider_config (se fornecido diretamente)
        2. model (configuração legacy de modelo único)
        3. simple_model/complex_model (configuração legacy multi-modelo)
        4. config_file YAML (se especificado)
        5. config.yaml no diretório atual (se existir e NENHUMA config de modelo foi fornecida)
        6. Valores padrão (gpt-4o-mini, gpt-4o)
        """
        # Verifica se alguma configuração de modelo foi fornecida explicitamente
        has_model_config = (
            self.model_provider_config is not None or
            self.model is not None or
            self.simple_model is not None or
            self.complex_model is not None
        )
        
        # Se model_provider_config já foi fornecido, usa ele
        if self.model_provider_config is not None:
            pass  # Já tem config, não faz nada
        
        # Se model (único) foi fornecido, cria config a partir dele
        elif self.model is not None:
            self.model_provider_config = ModelProviderConfig(
                simple=ModelConfig(
                    name=self.model,
                    api_base=self.api_base,
                    api_key=self.api_key
                ),
                complex=ModelConfig(
                    name=self.model,
                    api_base=self.api_base,
                    api_key=self.api_key
                )
            )
            self.use_multi_model = False
            self.simple_model = self.model
            self.complex_model = self.model
        
        # Se simple_model ou complex_model foram fornecidos, usa eles
        elif self.simple_model is not None or self.complex_model is not None:
            simple_name = self.simple_model or "gpt-4o-mini"
            complex_name = self.complex_model or "gpt-4o"
            self.model_provider_config = ModelProviderConfig(
                simple=ModelConfig(
                    name=simple_name,
                    api_base=self.api_base,
                    api_key=self.api_key
                ),
                complex=ModelConfig(
                    name=complex_name,
                    api_base=self.api_base,
                    api_key=self.api_key
                )
            )
        
        # Se config_file foi especificado, carrega dele
        elif self.config_file is not None:
            yaml_config = try_load_config_from_yaml(self.config_file)
            if yaml_config:
                self.model_provider_config = yaml_config
                self.use_multi_model = True
        
        # NENHUMA configuração foi fornecida - tenta carregar do config.yaml padrão
        elif not has_model_config:
            yaml_config = try_load_config_from_yaml("config.yaml")
            if yaml_config:
                self.model_provider_config = yaml_config
                self.use_multi_model = True
        
        # Fallback: usa valores padrão se ainda não tem config
        if self.model_provider_config is None:
            self.model_provider_config = ModelProviderConfig(
                simple=ModelConfig(
                    name="gpt-4o-mini",
                    api_base=self.api_base,
                    api_key=self.api_key
                ),
                complex=ModelConfig(
                    name="gpt-4o",
                    api_base=self.api_base,
                    api_key=self.api_key
                )
            )
        
        # Atualiza simple_model e complex_model para compatibilidade com código legacy
        if not self.simple_model:
            self.simple_model = self.model_provider_config.simple.name
        if not self.complex_model:
            self.complex_model = self.model_provider_config.complex.name
        
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore" # Ignore extra fields from .env
