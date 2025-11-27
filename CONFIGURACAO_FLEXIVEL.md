# Sistema de Configuração Flexível de Modelos

O sistema agora suporta configuração flexível de modelos, permitindo usar diferentes providers (LM Studio local, OpenAI comercial, etc.) para diferentes níveis de complexidade e até mesmo por tool específica.

## 🎯 Recursos

1. **Múltiplos Providers**: Use LM Studio local para algumas tarefas e OpenAI comercial para outras
2. **Configuração por Complexidade**: Modelo simples vs complexo com providers diferentes
3. **Configuração por Tool**: Override específico para ferramentas individuais
4. **Herança Inteligente**: Se não definido por tool, usa o modelo recomendado pela complexidade

## 📋 Estrutura de Configuração

### ModelConfig
Configuração de um modelo individual:
```python
ModelConfig(
    name="qwen/qwen3-coder-30b",           # Nome do modelo
    api_base="http://spark-0852.local:1234/v1",  # API base (None = provider padrão)
    api_key=""                              # API key (None = usa variáveis de ambiente)
)
```

### ModelProviderConfig
Configuração completa com simple, complex e overrides:
```python
ModelProviderConfig(
    simple=ModelConfig(...),                # Modelo para tarefas simples
    complex=ModelConfig(...),               # Modelo para tarefas complexas
    tool_overrides={                        # Opcional: overrides por tool
        "tool_name": ModelConfig(...)
    }
)
```

## 💡 Exemplos de Uso

### Exemplo 1: LM Studio (local) + OpenAI (comercial)

```python
from src.super_prompt.modern_ai_agent import ModernAIAgent
from src.super_prompt.config import AgentConfig
from src.super_prompt.model_config import ModelConfig, ModelProviderConfig

config = AgentConfig(
    model_provider_config=ModelProviderConfig(
        simple=ModelConfig(
            name="qwen/qwen3-coder-30b",
            api_base="http://spark-0852.local:1234/v1",  # LM Studio local
            api_key=""
        ),
        complex=ModelConfig(
            name="gpt-4o",
            api_base=None,  # OpenAI padrão (comercial)
            api_key=None    # Usa OPENAI_API_KEY do .env
        )
    ),
    use_multi_model=True,
    log_file="logs/agent_session.log",
    max_iterations=30
)

agent = ModernAIAgent(config=config)
```

**Como funciona:**
- **Iterações 1-2**: Usa `qwen/qwen3-coder-30b` do LM Studio local (modelo simples)
- **Iterações 3+**: Usa `gpt-4o` da OpenAI comercial (modelo complexo)
- **Ferramentas complexas**: Automaticamente usa `gpt-4o`

### Exemplo 2: Com Override por Tool

```python
config = AgentConfig(
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
            # Sempre usa GPT-4o para edição de código (mais preciso)
            "edit_lines": ModelConfig(
                name="gpt-4o",
                api_base=None,
                api_key=None
            ),
            # Usa GLM local para substituições simples
            "search_replace": ModelConfig(
                name="glm-4.6@iq1_m",
                api_base="http://spark-0852.local:1234/v1",
                api_key=""
            )
        }
    ),
    use_multi_model=True,
    log_file="logs/agent_session.log",
    max_iterations=30
)
```

**Como funciona:**
- **Tarefas simples**: `qwen/qwen3-coder-30b` (LM Studio)
- **Tarefas complexas**: `gpt-4o` (OpenAI)
- **Quando chama `edit_lines`**: Sempre usa `gpt-4o` (override)
- **Quando chama `search_replace`**: Sempre usa `glm-4.6@iq1_m` (override)
- **Outras tools**: Herdam do modelo baseado em complexidade

### Exemplo 3: Todos os Modelos Locais (LM Studio)

```python
config = AgentConfig(
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
```

### Exemplo 4: Todos os Modelos OpenAI (Comercial)

```python
config = AgentConfig(
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
```

## 🔄 Lógica de Seleção de Modelo

### Prioridade (do mais específico ao mais genérico):

1. **Tool Override**: Se a tool tem configuração específica, usa ela
2. **Complexidade da Tool**: Se a tool é "complex", usa `complex_model`
3. **Iteração**: 
   - Iterações 1-2: `simple_model`
   - Iterações 3+: `complex_model`
4. **Default**: `simple_model`

### Exemplo de Fluxo:

```
Iteração 1:
  - Tool: read_file (simple)
  - Modelo: qwen/qwen3-coder-30b (LM Studio)

Iteração 2:
  - Tool: edit_lines (tem override)
  - Modelo: gpt-4o (OpenAI) ← Override aplicado!

Iteração 3:
  - Tool: write_file (simple)
  - Modelo: gpt-4o (OpenAI) ← Iteração 3+, usa complex
```

## 🔧 Compatibilidade Legacy

O sistema antigo ainda funciona! Você pode usar:

```python
# Configuração legacy (ainda funciona)
config = AgentConfig(
    simple_model="gpt-4o-mini",
    complex_model="gpt-4o",
    api_base=None,
    use_multi_model=True
)
```

Isso será automaticamente convertido para o novo formato internamente.

## 📝 Notas Importantes

1. **api_base=None**: Usa o provider padrão (OpenAI para modelos OpenAI, etc.)
2. **api_key=None**: Usa variáveis de ambiente (OPENAI_API_KEY, etc.)
3. **Herança**: Tools sem override herdam do modelo baseado em complexidade
4. **Múltiplos Clientes**: O sistema cria clientes OpenAI separados para cada api_base diferente

## 🎨 Benefícios

- ✅ **Economia**: Use modelos locais (gratuitos) para tarefas simples
- ✅ **Qualidade**: Use modelos comerciais (pagos) para tarefas complexas
- ✅ **Flexibilidade**: Configure exatamente qual modelo usar para cada situação
- ✅ **Performance**: Otimize custo vs qualidade por tool específica

