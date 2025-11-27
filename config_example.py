#!/usr/bin/env python3
"""
Exemplos de configuração flexível do Modern AI Agent.

Este arquivo demonstra como configurar modelos de diferentes providers
(LM Studio local e OpenAI comercial) com configuração por nível e por tool.

NOVO: Agora também suporta configuração via arquivo YAML!
Veja config.yaml para exemplo de configuração.
"""

from src.super_prompt.modern_ai_agent import ModernAIAgent
from src.super_prompt.config import AgentConfig
from src.super_prompt.model_config import ModelConfig, ModelProviderConfig, load_config_from_yaml

# ============================================================================
# EXEMPLO 1: LM Studio (local) para simple + OpenAI (comercial) para complex
# ============================================================================

config1 = AgentConfig(
    model_provider_config=ModelProviderConfig(
        simple=ModelConfig(
            name="qwen/qwen3-coder-30b",
            api_base="http://spark-0852.local:1234/v1",  # LM Studio local
            api_key=""  # Não precisa de key para LM Studio
        ),
        complex=ModelConfig(
            name="gpt-4o",
            api_base=None,  # Usa OpenAI padrão
            api_key=None    # Usa OPENAI_API_KEY do .env
        )
    ),
    use_multi_model=True,
    log_file="logs/agent_session.log",
    max_iterations=30
)

# ============================================================================
# EXEMPLO 2: Com override por tool específica
# ============================================================================

config2 = AgentConfig(
    model_provider_config=ModelProviderConfig(
        simple=ModelConfig(
            name="qwen/qwen3-coder-30b",
            api_base="http://spark-0852.local:1234/v1",
            api_key=""
        ),
        complex=ModelConfig(
            name="gpt-4o",
            api_base=None,
            api_key=None
        ),
        tool_overrides={
            # Tool específica usa modelo diferente
            "edit_lines": ModelConfig(
                name="gpt-4o",  # Sempre usa GPT-4o para edição de código
                api_base=None,
                api_key=None
            ),
            "search_replace": ModelConfig(
                name="glm-4.6@iq1_m",  # Usa GLM local para substituições
                api_base="http://spark-0852.local:1234/v1",
                api_key=""
            )
        }
    ),
    use_multi_model=True,
    log_file="logs/agent_session.log",
    max_iterations=30
)

# ============================================================================
# EXEMPLO 3: Todos os modelos do LM Studio (local)
# ============================================================================

config3 = AgentConfig(
    model_provider_config=ModelProviderConfig(
        simple=ModelConfig(
            name="qwen/qwen3-coder-30b",
            api_base="http://spark-0852.local:1234/v1",
            api_key=""
        ),
        complex=ModelConfig(
            name="glm-4.6@iq1_m",
            api_base="http://spark-0852.local:1234/v1",
            api_key=""
        )
    ),
    use_multi_model=True,
    log_file="logs/agent_session.log",
    max_iterations=30
)

# ============================================================================
# EXEMPLO 4: Todos os modelos OpenAI (comercial)
# ============================================================================

config4 = AgentConfig(
    model_provider_config=ModelProviderConfig(
        simple=ModelConfig(
            name="gpt-4o-mini",
            api_base=None,  # OpenAI padrão
            api_key=None    # Do .env
        ),
        complex=ModelConfig(
            name="gpt-4o",
            api_base=None,
            api_key=None
        )
    ),
    use_multi_model=True,
    log_file="logs/agent_session.log",
    max_iterations=30
)

# ============================================================================
# EXEMPLO 5: Configuração legacy (ainda funciona)
# ============================================================================

config5 = AgentConfig(
    simple_model="gpt-4o-mini",
    complex_model="gpt-4o",
    api_base=None,  # OpenAI padrão
    use_multi_model=True,
    log_file="logs/agent_session.log",
    max_iterations=30
)

# ============================================================================
# EXEMPLO 6: Carrega configuração do arquivo YAML (NOVO!)
# ============================================================================

# Opção A: Carrega automaticamente de config.yaml (se existir)
config6a = AgentConfig()  # Detecta e carrega config.yaml automaticamente

# Opção B: Especifica o arquivo YAML explicitamente
config6b = AgentConfig(
    config_file="config.yaml",  # Caminho para o arquivo YAML
    log_file="logs/agent_session.log",
    max_iterations=30
)

# Opção C: Carrega YAML manualmente para mais controle
yaml_provider_config = load_config_from_yaml("config.yaml")
config6c = AgentConfig(
    model_provider_config=yaml_provider_config,
    use_multi_model=True,
    log_file="logs/agent_session.log",
    max_iterations=30
)

# ============================================================================
# USO
# ============================================================================

if __name__ == "__main__":
    # Escolha uma das configurações acima
    # config1-5: Configuração via código Python
    # config6a/b/c: Configuração via arquivo YAML (recomendado!)
    
    agent = ModernAIAgent(config=config6a)  # Usa config.yaml automaticamente
    
    # Execute uma tarefa
    result = agent.execute_task("Liste os arquivos Python no diretório atual")
    print(result)

