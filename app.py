from src.super_prompt.modern_ai_agent import ModernAIAgent
from src.super_prompt.config import AgentConfig
from src.super_prompt.model_config import ModelConfig, ModelProviderConfig

# ============================================================================
# CONFIGURAÇÃO FLEXÍVEL - Suporta múltiplos providers por modelo
# ============================================================================

# NOVO SISTEMA: Configuração flexível com diferentes providers
# Exemplo: LM Studio (local) para simple + OpenAI (comercial) para complex
# config = AgentConfig(
#     model_provider_config=ModelProviderConfig(
#         simple=ModelConfig(
#             name="qwen/qwen3-coder-30b",
#             api_base="http://spark-0852.local:1234/v1",  # LM Studio local
#             api_key=""
#         ),
#         complex=ModelConfig(
#             name="gpt-4o",
#             api_base=None,  # OpenAI padrão (comercial)
#             api_key=None    # Usa OPENAI_API_KEY do .env
#         ),
#         tool_overrides={
#             # Opcional: override por tool específica
#             "edit_lines": ModelConfig(
#                 name="gpt-4o",  # Sempre usa GPT-4o para edição
#                 api_base=None,
#                 api_key=None
#             )
#         }
#     ),
#     use_multi_model=True,
#     log_file="logs/agent_session.log",
#     max_iterations=30
# )

# ============================================================================
# CONFIGURAÇÃO LEGACY - Ainda funciona (compatibilidade)
# ============================================================================

# Exemplo 1: OpenAI (padrão)
# config = AgentConfig(
#     simple_model="gpt-4o-mini",
#     complex_model="gpt-4o",
#     use_multi_model=True,
#     log_file="logs/agent_session.log",
#     max_iterations=30
# )

# Exemplo 2: LM Studio (local) - Modelos disponíveis
# Quando você configura api_base para LM Studio, use o nome do modelo exatamente como aparece no LM Studio
# Opção A: Usando prefixo lm_studio/ (recomendado)
# config = AgentConfig(
#     simple_model="lm_studio/qwen2.5-7b-instruct",
#     complex_model="lm_studio/qwen2.5-7b-instruct",
#     api_base="http://localhost:1234/v1",
#     api_key="",
#     use_multi_model=False,
#     log_file="logs/agent_session.log",
#     max_iterations=30
# )

# Opção B: Modelos específicos do seu LM Studio (use o nome exato do modelo)
# Meta Llama 3.3 70B
# config = AgentConfig(
#     simple_model="meta/llama-3.3-70b",
#     complex_model="meta/llama-3.3-70b",
#     api_base="http://localhost:1234/v1",
#     api_key="",
#     use_multi_model=False,
#     log_file="logs/agent_session.log",
#     max_iterations=30
# )

# ============================================================================
# EXEMPLO: Configuração Flexível - LM Studio (local) + OpenAI (comercial)
# ============================================================================
# Este exemplo mostra como usar modelos de diferentes providers:
# - Simple: Qwen Coder 30B no LM Studio (local, gratuito)
# - Complex: GPT-4o na OpenAI (comercial, pago)
# ============================================================================

config = AgentConfig(
    model_provider_config=ModelProviderConfig(
        simple=ModelConfig(
            name="qwen/qwen3-coder-30b",
            api_base="http://spark-0852.local:1234/v1",  # LM Studio local
            api_key=""
        ),
        complex=ModelConfig(
            name="gpt-5.1",
            api_base=None,  # OpenAI padrão (comercial)
            api_key=None    # Usa OPENAI_API_KEY do .env
        )
    ),
    use_multi_model=True,
    log_file="logs/agent_session.log",
    max_iterations=30
)

# ============================================================================
# CONFIGURAÇÃO LEGACY (ainda funciona)
# ============================================================================
# config = AgentConfig(
#     simple_model="qwen/qwen3-coder-30b",
#     complex_model="openai/gpt-oss-120b",
#     api_base="http://spark-0852.local:1234/v1",
#     api_key="",
#     use_multi_model=True,
#     log_file="logs/agent_session.log",
#     max_iterations=30
# )

# GPT OSS 120B (modelo grande)
# config = AgentConfig(
#     simple_model="openai/gpt-oss-120b",
#     complex_model="openai/gpt-oss-120b",
#     api_base="http://spark-0852.local:1234/v1",
#     api_key="",
#     use_multi_model=False,
#     log_file="logs/agent_session.log",
#     max_iterations=30
# )

# GLM 4.6
# config = AgentConfig(
#     simple_model="glm-4.6@iq1_m",
#     complex_model="glm-4.6@iq1_m",
#     api_base="http://localhost:1234/v1",
#     api_key="",
#     use_multi_model=False,
#     log_file="logs/agent_session.log",
#     max_iterations=30
# )

# Microsoft Phi 4 Reasoning Plus
# config = AgentConfig(
#     simple_model="microsoft/phi-4-reasoning-plus",
#     complex_model="microsoft/phi-4-reasoning-plus",
#     api_base="http://localhost:1234/v1",
#     api_key="",
#     use_multi_model=False,
#     log_file="logs/agent_session.log",
#     max_iterations=30
# )

# Exemplo 3: Ollama (local)
# config = AgentConfig(
#     simple_model="ollama/llama3",
#     complex_model="ollama/llama3",
#     api_base="http://localhost:11434",
#     use_multi_model=False,
#     log_file="logs/agent_session.log",
#     max_iterations=30
# )

# Exemplo 4: Anthropic Claude
# config = AgentConfig(
#     simple_model="claude-3-haiku-20240307",
#     complex_model="claude-3-opus-20240229",
#     use_multi_model=True,
#     api_key="sk-ant-...",  # Ou configure ANTHROPIC_API_KEY no .env
#     log_file="logs/agent_session.log",
#     max_iterations=30
# )

# Exemplo 5: Groq (rápido e gratuito)
# config = AgentConfig(
#     simple_model="groq/llama-3.1-8b-instant",
#     complex_model="groq/llama-3.1-70b-versatile",
#     use_multi_model=True,
#     api_key="gsk_...",  # Ou configure GROQ_API_KEY no .env
#     log_file="logs/agent_session.log",
#     max_iterations=30
# )

# Configuração atual (OpenAI)
# config = AgentConfig(
#     simple_model="gpt-4o-mini",
#     complex_model="gpt-4o",
#     use_multi_model=True,
#     log_file="logs/agent_session.log",
#     max_iterations=3  # Limite global (padrão: 30, range: 1-1000)
# )

# ============================================================================
# ARQUITETURA HÍBRIDA DE FASES COGNITIVAS
# ============================================================================
# Quando use_multi_model=True, o agente executa em FASES:
#
# FASE 1: PLANEJAMENTO (🧠 modelo complexo)
#   → Analisa a tarefa e cria um plano estruturado
#   → Sempre usa o modelo mais capaz para garantir bom planejamento
#
# FASE 2: EXECUÇÃO (⚡ modelo simples)
#   → Executa ferramentas atômicas (read_file, edit_lines, run_command...)
#   → Usa modelo mais rápido/barato para tarefas simples
#
# META-FERRAMENTAS COGNITIVAS (🧠 modelo complexo - sob demanda):
#   → analyze_error: Analisa erros e sugere correções
#   → replan_approach: Reformula estratégia quando algo falha
#   → validate_result: Verifica se ação foi bem-sucedida
#   → progress_checkpoint: Registra progresso em tarefas longas
#
# FASE 3: VALIDAÇÃO (🧠 modelo complexo)
#   → Valida se a tarefa foi realmente concluída
#   → Identifica problemas e sugestões de melhoria
#
# Você pode controlar as fases com:
#   agent.execute_task(task, skip_planning=True)   # Pula planejamento
#   agent.execute_task(task, skip_validation=True) # Pula validação
# ============================================================================

agent = ModernAIAgent(config=config)

# Uso simples - o agente decide o que fazer
# agent.execute_task("""crie uma aplicaçao simples usando fastapi de nome main2.py. Que tenham os seguintes metodos: 
# uppercase_nome(nome: str) -> str: que recebe um nome e retorna o mesmo em uppercase. e lowercase_nome(nome: str) -> str: 
# que recebe um nome e retorna o mesmo em lowercase.""")

# Exemplo: tarefa com limite de iterações personalizado
# agent.execute_task(
#     "crie e teste uma aplicaçao simples usando fastapi de nome main.py. adicione e instale dependencias via requirements.txt",
#     max_iterations=100  # Limite específico para esta tarefa (sobrescreve o configurado globalmente)
# )

agent.execute_task("crie e teste uma aplicaçao simples usando fastapi de nome main.py. adicione e instale dependencias via requirements.txt")

# agent.execute_task("""
# adicione um metodo http GET que recebe um parametro 'nome' 
# e retorna o mesmo em uppercase (main.py).
# """)

# agent.execute_task("""
# chame o metodo uppercase_nome(nome) da aplicação main.py usando curl shell. 
# (verifique se a aplicação esta rodando e nao, execute em background com nohup antes de realizar a chamada. Desligue a aplicação apos a chamada.)
# nome: "joao"
# resultado: "JOAO"
# """)
# agent.execute_task("""
# no arquivo main.py, antes de dar upper acrescente a palavra "_TESTE" como sufixo no nome passado como parametro.
# """)
# agent.execute_task("""
# no arquivo main.py, apique teste pytest para o metodo uppercase_nome.
# """)

# agent.execute_task("""
# no arquivo tests/test_main.py, adicione sys.path.append(str(Path(__file__).resolve().parents[1])) para que o arquivo main.py seja encontrado pelo pytest.
# """)

# agent.execute_task("""
# crie um arquivo do tipo .md com o nome prompt1.md e adicione 
# um prompt de um vende dor de seguros chamado joao.
# """)

# agent.execute_task("""
# crie prompt2.md baseado em prompt1.md porém com foco na pergunta do usuário. 
# O objetivo é tornarmos o prompt1 mais aderente a pergunta do usuário. 
# Porém mantendo o contexto do prompt1 e as orientaçoes essenciais.
# Pergunta do usuário: "como faço para contratar um seguro de vida?"
# """)
# agent.execute_task("""
# crie prompt3.md baseado em prompt1.md porém com foco na pergunta do usuário. 
# O objetivo é tornarmos o prompt1 mais aderente a pergunta do usuário. 
# Porém mantendo o contexto do prompt1 e as orientaçoes essenciais.
# Pergunta do usuário: "Voce é uma IA?"
# """)