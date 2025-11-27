"""
Cognitive meta-tools for the Modern AI Agent.

These tools handle higher-level reasoning tasks like error analysis,
replanning, and result validation. They are marked as "complex" and
should be executed by the more capable model.
"""
from typing import Optional, List, Dict, Any
from .tool_decorator import tool


@tool(
    description="""🧠 ANÁLISE DE ERRO - Use quando uma ferramenta falhar ou retornar resultado inesperado.
    
Esta ferramenta analisa erros e sugere ações corretivas. Use quando:
- Uma ferramenta retornou erro
- O resultado não é o esperado
- Você não sabe como proceder após uma falha

Retorna análise estruturada com:
- Causa provável do erro
- Impacto no plano atual
- Ações sugeridas para correção""",
    parameters={
        "error_message": {"type": "string", "description": "A mensagem de erro ou resultado inesperado"},
        "tool_name": {"type": "string", "description": "Nome da ferramenta que falhou"},
        "tool_args": {"type": "string", "description": "Argumentos usados na ferramenta (JSON string)"},
        "context": {"type": "string", "description": "Contexto da tarefa atual e o que estava tentando fazer"}
    },
    required=["error_message", "tool_name", "context"],
    complexity="complex"
)
def analyze_error(error_message: str, tool_name: str, context: str, tool_args: str = "{}") -> str:
    """
    Analisa um erro e retorna informações estruturadas para ajudar o LLM a decidir.
    Esta é uma "pseudo-ferramenta" - o conteúdo real da análise será feito pelo LLM
    ao processar a resposta desta ferramenta.
    """
    return f"""🔍 ANÁLISE DE ERRO SOLICITADA

📛 Ferramenta: {tool_name}
📋 Argumentos: {tool_args}
❌ Erro: {error_message}
📝 Contexto: {context}

⚠️ INSTRUÇÕES PARA O AGENTE:
1. Analise a causa raiz deste erro
2. Verifique se os argumentos estavam corretos
3. Considere se há uma abordagem alternativa
4. Se necessário, use 'replan_approach' para ajustar sua estratégia

POSSÍVEIS CAUSAS COMUNS:
- Arquivo não existe → use list_files para verificar
- Permissão negada → verifique o caminho
- Sintaxe inválida → revise o código/argumentos
- Dependência faltando → instale com run_command"""


@tool(
    description="""🔄 RE-PLANEJAMENTO - Use quando precisar mudar sua estratégia após um erro ou obstáculo.

Esta ferramenta ajuda a reformular a abordagem quando:
- A estratégia atual não está funcionando
- Descobriu nova informação que muda o plano
- Múltiplos erros indicam problema na abordagem

Retorna um novo plano estruturado.""",
    parameters={
        "original_goal": {"type": "string", "description": "O objetivo original da tarefa"},
        "current_situation": {"type": "string", "description": "Situação atual - o que foi feito e o que falhou"},
        "obstacles": {"type": "string", "description": "Lista de obstáculos encontrados"},
        "new_information": {"type": "string", "description": "Novas informações descobertas durante execução"}
    },
    required=["original_goal", "current_situation", "obstacles"],
    complexity="complex"
)
def replan_approach(
    original_goal: str, 
    current_situation: str, 
    obstacles: str, 
    new_information: str = ""
) -> str:
    """
    Solicita re-planejamento da abordagem.
    """
    return f"""🔄 RE-PLANEJAMENTO SOLICITADO

🎯 Objetivo Original: {original_goal}

📍 Situação Atual:
{current_situation}

🚧 Obstáculos Encontrados:
{obstacles}

💡 Novas Informações:
{new_information or "Nenhuma"}

⚠️ INSTRUÇÕES PARA O AGENTE:
1. Revise sua estratégia considerando os obstáculos
2. Identifique uma abordagem alternativa
3. Crie um novo plano passo-a-passo
4. Execute o novo plano

DICAS DE RE-PLANEJAMENTO:
- Se arquivo não existe, crie-o
- Se estrutura diferente, adapte-se
- Se dependência falta, instale primeiro
- Se permissão negada, tente caminho alternativo"""


@tool(
    description="""✅ VALIDAÇÃO DE RESULTADO - Use para verificar se uma ação foi bem-sucedida.

Esta ferramenta ajuda a confirmar que:
- O arquivo foi realmente modificado como esperado
- O comando produziu o resultado correto
- A tarefa parcial foi concluída

Use após operações importantes para garantir sucesso.""",
    parameters={
        "action_taken": {"type": "string", "description": "Descrição da ação que foi executada"},
        "expected_result": {"type": "string", "description": "O que você esperava que acontecesse"},
        "actual_result": {"type": "string", "description": "O que realmente aconteceu (resultado da ferramenta)"},
        "verification_method": {"type": "string", "description": "Como verificar se funcionou (ex: 'read_file', 'run_command ls')"}
    },
    required=["action_taken", "expected_result", "actual_result"],
    complexity="complex"
)
def validate_result(
    action_taken: str,
    expected_result: str,
    actual_result: str,
    verification_method: str = ""
) -> str:
    """
    Solicita validação de um resultado.
    """
    success_indicators = [
        "✓", "sucesso", "success", "concluído", "completed", 
        "criado", "created", "editado", "edited", "ok"
    ]
    
    likely_success = any(ind.lower() in actual_result.lower() for ind in success_indicators)
    error_indicators = ["✗", "erro", "error", "falha", "failed", "não encontrado", "not found"]
    likely_failure = any(ind.lower() in actual_result.lower() for ind in error_indicators)
    
    status = "⚠️ INCERTO"
    if likely_success and not likely_failure:
        status = "✅ PROVÁVEL SUCESSO"
    elif likely_failure:
        status = "❌ PROVÁVEL FALHA"
    
    return f"""✅ VALIDAÇÃO DE RESULTADO

📋 Ação Executada: {action_taken}
🎯 Resultado Esperado: {expected_result}
📊 Resultado Obtido: {actual_result}

{status}

🔍 Método de Verificação Sugerido: {verification_method or "Use read_file ou list_files para confirmar"}

⚠️ INSTRUÇÕES PARA O AGENTE:
1. Compare o resultado esperado com o obtido
2. Se incerto, execute a verificação sugerida
3. Se falhou, use 'analyze_error' para entender o problema
4. Se sucesso, prossiga para o próximo passo"""


@tool(
    description="""📊 CHECKPOINT DE PROGRESSO - Use para registrar e avaliar o progresso da tarefa.

Esta ferramenta ajuda a:
- Manter registro do que foi feito
- Avaliar quanto falta para concluir
- Identificar se está no caminho certo

Use periodicamente em tarefas longas.""",
    parameters={
        "task_description": {"type": "string", "description": "Descrição da tarefa principal"},
        "steps_completed": {"type": "string", "description": "Lista de passos já completados"},
        "steps_remaining": {"type": "string", "description": "Lista de passos que ainda faltam"},
        "confidence_level": {"type": "string", "description": "Nível de confiança: 'alto', 'médio', 'baixo'"}
    },
    required=["task_description", "steps_completed", "steps_remaining"],
    complexity="complex"
)
def progress_checkpoint(
    task_description: str,
    steps_completed: str,
    steps_remaining: str,
    confidence_level: str = "médio"
) -> str:
    """
    Registra checkpoint de progresso.
    """
    return f"""📊 CHECKPOINT DE PROGRESSO

🎯 Tarefa: {task_description}

✅ Passos Completados:
{steps_completed}

⏳ Passos Restantes:
{steps_remaining}

📈 Nível de Confiança: {confidence_level.upper()}

⚠️ INSTRUÇÕES PARA O AGENTE:
1. Avalie se os passos completados foram bem-sucedidos
2. Verifique se os passos restantes ainda fazem sentido
3. Se confiança baixa, considere usar 'replan_approach'
4. Continue com o próximo passo da lista"""

