#!/usr/bin/env python3
"""
Modern AI Code Agent - Arquitetura 2025
Implementação moderna usando OpenAI Function Calling nativo
Baseado em melhores práticas de arquitetura de agentes
"""

import os
import json
import subprocess
import signal
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box
from rich.syntax import Syntax

from code_agent import CodeAgent


class ModernAIAgent:
    """
    Agente de IA moderno usando OpenAI Function Calling.
    
    Arquitetura baseada em:
    - OpenAI Function Calling (nativo, eficiente)
    - Pattern ReAct (Reasoning + Acting)
    - Tool-use pattern
    - Separação clara entre planejamento e execução
    
    Benefícios:
    - Mais confiável que LangChain clássico
    - Menos dependências
    - Melhor controle sobre o fluxo
    - Custos otimizados
    """
    
    def __init__(
        self,
        workspace: str = ".",
        model: Optional[str] = None,
        simple_model: str = "gpt-4o-mini",
        complex_model: str = "gpt-4o",
        use_multi_model: bool = False,
        max_iterations: int = 30,
        verbose: bool = True,
        log_file: Optional[str] = None
    ):
        """
        Inicializa o Modern AI Agent.
        
        Args:
            workspace: Diretório de trabalho
            model: Modelo OpenAI fixo (se fornecido, ignora simple_model/complex_model).
                   Se None e use_multi_model=True, usa modelos diferentes por ferramenta.
                   Opções disponíveis:
                   GPT-5 (2025):
                   - 'gpt-5' (mais poderoso, $1.25/$10 por M tokens)
                   - 'gpt-5-mini' (barato, $0.25/$2 por M tokens)
                   - 'gpt-5-nano' (ultra-barato, $0.05/$0.40 por M tokens)
                   GPT-4:
                   - 'gpt-4o' (otimizado)
                   - 'gpt-4o-mini' (padrão, mais barato)
                   - 'gpt-4-turbo'
            simple_model: Modelo para ferramentas simples (padrão: 'gpt-4o-mini')
                         Usado em: leitura, listagem, edições simples
            complex_model: Modelo para ferramentas complexas (padrão: 'gpt-4o')
                          Usado em: planejamento, validação, análise, crítica
            use_multi_model: Se True, usa modelos diferentes por tipo de ferramenta
            max_iterations: Máximo de iterações tool-call (padrão: 30)
            verbose: Mostra logs detalhados
            log_file: Caminho do arquivo de log (ex: 'agent.log', 'logs/session.txt')
                     Se fornecido, salva íntegra de todo o fluxo de execução
        """
        self.console = Console()
        self.workspace = Path(workspace).resolve()
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.use_multi_model = use_multi_model
        
        # 🆕 Sistema de logging
        self.log_file = log_file
        self.log_handle = None
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_handle = open(log_path, 'a', encoding='utf-8')
            self._write_log(f"\n{'='*80}\n")
            self._write_log(f"🚀 NOVA SESSÃO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._write_log(f"{'='*80}\n")
        
        # Valida modelos
        valid_models = [
            # GPT-5 (2025)
            'gpt-5', 'gpt-5-mini', 'gpt-5-nano',
            # GPT-4
            'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-4-turbo-preview',
            # GPT-3.5 (legacy)
            'gpt-3.5-turbo'
        ]
        
        # Se model fornecido, usa modelo fixo
        if model:
            if model not in valid_models:
                self.console.print(f"[yellow]⚠️ Aviso: Modelo '{model}' pode não ser válido.[/yellow]")
                self.console.print(f"[yellow]Modelos válidos: {', '.join(valid_models[:6])}...[/yellow]")
            self.default_model = model
            self.simple_model = model
            self.complex_model = model
            self.use_multi_model = False
        else:
            # Valida modelos simples e complexos
            if simple_model not in valid_models:
                self.console.print(f"[yellow]⚠️ Aviso: Modelo simples '{simple_model}' pode não ser válido.[/yellow]")
            if complex_model not in valid_models:
                self.console.print(f"[yellow]⚠️ Aviso: Modelo complexo '{complex_model}' pode não ser válido.[/yellow]")
            
            self.default_model = simple_model
            self.simple_model = simple_model
            self.complex_model = complex_model
        
        # 🆕 Categorização de ferramentas por complexidade
        self.tool_complexity: Dict[str, str] = {}  # tool_name -> "simple" ou "complex"
        
        # Carrega API key
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY não encontrada no .env")
        
        # Inicializa clientes
        self.client = OpenAI(api_key=api_key)
        self.code_agent = CodeAgent(workspace)
        
        # Registra ferramentas (tools)
        self.tools_registry: Dict[str, Callable] = {}
        self.tools_schema: List[Dict[str, Any]] = []
        self._register_tools()
        
        # 🆕 MEMÓRIA: Histórico de conversação e resumos
        self.max_history_tasks: int = 3  # Mantém últimas 3 tarefas completas
        self.conversation_history: List[List[Dict[str, Any]]] = []  # Mensagens completas das últimas N tarefas
        self.task_summaries: List[Dict[str, Any]] = []  # Resumos de TODAS as tarefas executadas
        self.task_counter: int = 0  # Contador de tarefas
        
        if self.verbose:
            if self.use_multi_model:
                self.console.print(
                    f"[green]✓ Modern AI Agent inicializado[/green]\n"
                    f"[dim]  Modo: Multi-Model (seleção automática)[/dim]\n"
                    f"[dim]  ⚡ Simple: {self.simple_model}[/dim]\n"
                    f"[dim]  🧠 Complex: {self.complex_model}[/dim]\n"
                    f"[dim]  Workspace: {workspace}[/dim]\n"
                    f"[dim]  Tools: {len(self.tools_registry)} ({sum(1 for c in self.tool_complexity.values() if c == 'complex')} complexas)[/dim]"
                )
            else:
                self.console.print(
                    f"[green]✓ Modern AI Agent inicializado[/green]\n"
                    f"[dim]  Modelo: {self.default_model}[/dim]\n"
                    f"[dim]  Workspace: {workspace}[/dim]\n"
                    f"[dim]  Tools: {len(self.tools_registry)}[/dim]"
                )
    
    def __del__(self):
        """Fecha o arquivo de log ao destruir o objeto"""
        if self.log_handle:
            try:
                self._write_log(f"\n{'='*80}\n")
                self._write_log(f"🏁 FIM DA SESSÃO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self._write_log(f"{'='*80}\n\n")
                self.log_handle.close()
            except:
                pass
    
    def _write_log(self, message: str):
        """
        Escreve mensagem no arquivo de log.
        
        Args:
            message: Mensagem a ser escrita
        """
        if self.log_handle:
            try:
                self.log_handle.write(message)
                self.log_handle.flush()  # Garante escrita imediata
            except Exception as e:
                if self.verbose:
                    self.console.print(f"[yellow]⚠️ Erro ao escrever log: {e}[/yellow]")
    
    def _register_tools(self):
        """Registra todas as ferramentas disponíveis"""
        
        # Tool 0: Verificar e sugerir ação (NOVO)
        self.register_tool(
            name="check_file_and_suggest_action",
            description="SEMPRE use isto ANTES de criar/modificar arquivo. Verifica se arquivo existe e sugere a melhor ação (criar, editar, ou usar outro nome).",
            parameters={
                "filepath": {
                    "type": "string",
                    "description": "Caminho do arquivo que você quer criar ou modificar"
                },
                "intended_action": {
                    "type": "string",
                    "description": "O que você pretende fazer (ex: 'criar app fastapi', 'adicionar rota', 'corrigir bug')"
                }
            },
            required=["filepath", "intended_action"],
            function=self._tool_check_file_and_suggest,
            complexity="complex"  # 🧠 Análise e sugestão inteligente
        )
        
        # Tool 0b: Planejar mudanças (NOVO - CRÍTICO)
        self.register_tool(
            name="plan_file_changes",
            description="🆕 FERRAMENTA CRÍTICA! Use ANTES de fazer múltiplas edições. Planeja as mudanças necessárias e retorna estratégia. SEMPRE planeje antes de executar!",
            parameters={
                "filepath": {
                    "type": "string",
                    "description": "Arquivo que será modificado"
                },
                "goal": {
                    "type": "string",
                    "description": "O que você quer alcançar (ex: 'adicionar método uppercase e teste')"
                },
                "current_understanding": {
                    "type": "string",
                    "description": "Seu entendimento da estrutura atual do arquivo"
                }
            },
            required=["filepath", "goal"],
            function=self._tool_plan_changes,
            complexity="complex"  # 🧠 Planejamento estratégico
        )
        
        # Tool 0c: Validar Python (NOVO)
        self.register_tool(
            name="validate_python_syntax",
            description="Valida se um arquivo Python tem sintaxe válida. Use APÓS edições para garantir que não quebrou nada.",
            parameters={
                "filepath": {
                    "type": "string",
                    "description": "Arquivo Python para validar"
                }
            },
            required=["filepath"],
            function=self._tool_validate_python,
            complexity="complex"  # 🧠 Validação e análise de sintaxe
        )
        
        # Tool 0d: Sugerir ponto de inserção (NOVO - CRÍTICO)
        self.register_tool(
            name="suggest_insertion_point",
            description="🆕 CRÍTICO! Sugere ONDE inserir código (linha exata). Use ANTES de edit_lines para garantir posicionamento correto seguindo boas práticas.",
            parameters={
                "filepath": {
                    "type": "string",
                    "description": "Arquivo onde vai inserir código"
                },
                "code_type": {
                    "type": "string",
                    "description": "Tipo de código a inserir: 'import', 'class', 'function', 'route', 'test', 'constant', 'main_block'"
                },
                "description": {
                    "type": "string",
                    "description": "Descrição do código (ex: 'rota GET /uppercase', 'função de teste')"
                }
            },
            required=["filepath", "code_type"],
            function=self._tool_suggest_insertion,
            complexity="complex"  # 🧠 Análise de estrutura e PEP 8
        )
        
        # Tool 0e: Validar organização (NOVO)
        self.register_tool(
            name="validate_code_organization",
            description="Valida se arquivo Python está bem organizado (ordem correta, boas práticas). Use para verificar qualidade.",
            parameters={
                "filepath": {
                    "type": "string",
                    "description": "Arquivo Python para validar organização"
                }
            },
            required=["filepath"],
            function=self._tool_validate_organization,
            complexity="complex"  # 🧠 Validação de qualidade e boas práticas
        )
        
        # Tool 0f: Inserir linhas (NOVO - CRÍTICO para evitar substituições)
        self.register_tool(
            name="insert_lines",
            description="🆕 CRÍTICO! INSERE código APÓS uma linha (não substitui). Use quando quiser ADICIONAR código novo sem remover existente.",
            parameters={
                "filepath": {
                    "type": "string",
                    "description": "Arquivo onde inserir"
                },
                "after_line": {
                    "type": "integer",
                    "description": "Insere APÓS esta linha (ex: after_line=8 insere entre linha 8 e 9)"
                },
                "content": {
                    "type": "string",
                    "description": "Conteúdo a inserir"
                }
            },
            required=["filepath", "after_line", "content"],
            function=self._tool_insert_lines,
            complexity="simple"  # ✏️ Edição direta
        )
        
        # Tool 1: Ler arquivo
        self.register_tool(
            name="read_file",
            description="Lê o conteúdo completo de um arquivo do workspace",
            parameters={
                "filepath": {
                    "type": "string",
                    "description": "Caminho relativo do arquivo no workspace"
                }
            },
            required=["filepath"],
            function=self._tool_read_file,
            complexity="simple"  # 📖 Leitura simples
        )
        
        # Tool 2: Escrever arquivo (com proteção)
        self.register_tool(
            name="write_file",
            description="Cria um novo arquivo. BLOQUEIA se arquivo já existe (proteção). Para sobrescrever use force_write_file.",
            parameters={
                "filepath": {
                    "type": "string",
                    "description": "Caminho do arquivo a criar"
                },
                "content": {
                    "type": "string",
                    "description": "Conteúdo completo a escrever"
                }
            },
            required=["filepath", "content"],
            function=self._tool_write_file,
            complexity="simple"  # ✏️ Escrita direta
        )
        
        # Tool 2b: Forçar escrita (sobrescrever)
        self.register_tool(
            name="force_write_file",
            description="Sobrescreve um arquivo EXISTENTE forçadamente. Use APENAS quando tiver certeza. Cria backup automático.",
            parameters={
                "filepath": {
                    "type": "string",
                    "description": "Caminho do arquivo a sobrescrever"
                },
                "content": {
                    "type": "string",
                    "description": "Novo conteúdo completo"
                },
                "reason": {
                    "type": "string",
                    "description": "Motivo da sobrescrita (obrigatório para audit)"
                }
            },
            required=["filepath", "content", "reason"],
            function=self._tool_force_write_file,
            complexity="simple"  # ✏️ Escrita direta (com audit)
        )
        
        # Tool 3: Buscar e substituir
        self.register_tool(
            name="search_replace",
            description="Busca e substitui texto em um arquivo",
            parameters={
                "filepath": {
                    "type": "string",
                    "description": "Caminho do arquivo"
                },
                "search": {
                    "type": "string",
                    "description": "Texto exato a buscar"
                },
                "replace": {
                    "type": "string",
                    "description": "Texto substituto"
                }
            },
            required=["filepath", "search", "replace"],
            function=self._tool_search_replace,
            complexity="simple"  # ✏️ Substituição direta
        )
        
        # Tool 4: Editar linhas
        self.register_tool(
            name="edit_lines",
            description="Edita linhas específicas de um arquivo (1-indexed)",
            parameters={
                "filepath": {
                    "type": "string",
                    "description": "Caminho do arquivo"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Linha inicial (1-indexed)"
                },
                "end_line": {
                    "type": "integer",
                    "description": "Linha final (1-indexed, inclusiva)"
                },
                "new_content": {
                    "type": "string",
                    "description": "Novo conteúdo para as linhas"
                }
            },
            required=["filepath", "start_line", "end_line", "new_content"],
            function=self._tool_edit_lines,
            complexity="simple"  # ✏️ Edição direta
        )
        
        # Tool 4b: Deletar linhas (NOVO)
        self.register_tool(
            name="delete_lines",
            description="🗑️ Remove linhas específicas de um arquivo. Suporta range (start_line-end_line) ou lista de índices (line_indices).",
            parameters={
                "filepath": {
                    "type": "string",
                    "description": "Caminho do arquivo"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Linha inicial do range (1-indexed, inclusiva). Use com end_line para remover range."
                },
                "end_line": {
                    "type": "integer",
                    "description": "Linha final do range (1-indexed, inclusiva). Use com start_line para remover range."
                },
                "line_indices": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Lista de índices de linhas para remover (0-indexed). Ex: [0, 10, 23] remove linhas 1, 11, 24. Use este OU start_line/end_line."
                }
            },
            required=["filepath"],
            function=self._tool_delete_lines,
            complexity="simple"  # 🗑️ Deleção direta
        )
        
        # Tool 5: Listar arquivos
        self.register_tool(
            name="list_files",
            description="Lista arquivos no workspace com um padrão glob",
            parameters={
                "pattern": {
                    "type": "string",
                    "description": "Padrão glob (ex: '*.py', '**/*.js')",
                    "default": "*"
                }
            },
            required=[],
            function=self._tool_list_files,
            complexity="simple"  # 📁 Listagem simples
        )
        
        # Tool 6: Mostrar arquivo
        self.register_tool(
            name="show_file",
            description="Mostra um arquivo com syntax highlighting",
            parameters={
                "filepath": {
                    "type": "string",
                    "description": "Caminho do arquivo"
                }
            },
            required=["filepath"],
            function=self._tool_show_file,
            complexity="simple"  # 👁️ Visualização simples
        )
        
        # Tool 7: Executar comando shell
        self.register_tool(
            name="run_command",
            description="Executa um comando shell único (ex: ls, pwd, git status). CUIDADO: use apenas comandos seguros de leitura.",
            parameters={
                "command": {
                    "type": "string",
                    "description": "Comando shell a executar (ex: 'ls -la', 'pwd', 'git status')"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout em segundos (padrão: 30)",
                    "default": 30
                }
            },
            required=["command"],
            function=self._tool_run_command,
            complexity="simple"  # 🔧 Execução direta
        )
        
        # Tool 8: Executar script shell
        self.register_tool(
            name="run_script",
            description="Executa um script shell completo (múltiplas linhas). Use para operações batch.",
            parameters={
                "script": {
                    "type": "string",
                    "description": "Script shell completo a executar"
                },
                "shell": {
                    "type": "string",
                    "description": "Shell a usar (bash, sh, zsh). Padrão: bash",
                    "default": "bash"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout em segundos (padrão: 60)",
                    "default": 60
                }
            },
            required=["script"],
            function=self._tool_run_script,
            complexity="simple"  # 🔧 Execução direta
        )
    
    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        required: List[str],
        function: Callable,
        complexity: str = "simple"
    ):
        """
        Registra uma nova ferramenta.
        
        Args:
            name: Nome da ferramenta
            description: Descrição do que faz
            parameters: Dicionário de parâmetros
            required: Lista de parâmetros obrigatórios
            function: Função Python a executar
            complexity: "simple" (modelo barato) ou "complex" (modelo poderoso)
                       - simple: leitura, listagem, edições diretas
                       - complex: planejamento, validação, análise, crítica, debug
        """
        # Registra função
        self.tools_registry[name] = function
        
        # 🆕 Registra complexidade
        self.tool_complexity[name] = complexity
        
        # Cria schema OpenAI
        self.tools_schema.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required
                }
            }
        })
    
    def _select_model_for_tools(self, tool_calls: List[Any]) -> str:
        """
        Seleciona o modelo apropriado baseado nas ferramentas sendo chamadas.
        
        Args:
            tool_calls: Lista de tool_calls da resposta da API
            
        Returns:
            Nome do modelo a usar ("simple" ou "complex")
        """
        if not self.use_multi_model:
            # Modo single-model
            return self.default_model
        
        # Analisa complexidade das ferramentas sendo chamadas
        has_complex_tool = False
        for tool_call in tool_calls:
            if isinstance(tool_call, dict):
                tool_name = tool_call.get("function", {}).get("name")
            else:
                tool_name = getattr(tool_call, "function", None)
                if tool_name:
                    tool_name = getattr(tool_name, "name", None)
            
            if tool_name and self.tool_complexity.get(tool_name) == "complex":
                has_complex_tool = True
                break
        
        # Se tem pelo menos 1 ferramenta complexa, usa modelo poderoso
        model_to_use = self.complex_model if has_complex_tool else self.simple_model
        
        if self.verbose and has_complex_tool:
            self.console.print(f"[dim]🧠 Usando modelo poderoso ({model_to_use}) para ferramentas complexas[/dim]")
        
        return model_to_use
    
    # Implementações das ferramentas
    
    def _tool_plan_changes(self, filepath: str, goal: str, current_understanding: str = "") -> str:
        """
        🆕 FERRAMENTA CRÍTICA DE PLANEJAMENTO
        
        Ajuda o agente a PLANEJAR antes de EXECUTAR.
        Previne loops de edições ineficientes.
        """
        try:
            file_path = self.workspace / filepath
            
            if not file_path.exists():
                return f"❌ Arquivo {filepath} não existe. Use write_file para criar."
            
            # Lê arquivo atual
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            lines = current_content.splitlines()
            total_lines = len(lines)
            
            plan = f"""
📋 **PLANO DE MODIFICAÇÃO** - {filepath}

🎯 **OBJETIVO:**
{goal}

📊 **ESTADO ATUAL:**
- Total de linhas: {total_lines}
- Tamanho: {len(current_content)} caracteres

📝 **ESTRUTURA ATUAL:**
"""
            
            # Analisa estrutura (funções, classes, imports)
            imports = []
            functions = []
            classes = []
            decorators = []
            
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith('import ') or stripped.startswith('from '):
                    imports.append(f"  Linha {i}: {stripped[:60]}")
                elif stripped.startswith('class '):
                    classes.append(f"  Linha {i}: {stripped[:60]}")
                elif stripped.startswith('def '):
                    functions.append(f"  Linha {i}: {stripped[:60]}")
                elif stripped.startswith('@'):
                    decorators.append(f"  Linha {i}: {stripped[:60]}")
            
            if imports:
                plan += "\n**Imports:**\n" + "\n".join(imports[:10])
            if classes:
                plan += "\n\n**Classes:**\n" + "\n".join(classes[:10])
            if functions:
                plan += "\n\n**Funções:**\n" + "\n".join(functions[:10])
            if decorators:
                plan += "\n\n**Decorators:**\n" + "\n".join(decorators[:10])
            
            plan += f"""

⚠️ **RECOMENDAÇÕES ESTRATÉGICAS:**

1. **NÃO faça edições linha por linha!**
   - Edições incrementais causam loops infinitos
   - Planeje blocos completos

2. **Use search_replace para mudanças pontuais**
   - Substituir imports
   - Trocar valores específicos
   - Renomear variáveis

3. **Use edit_lines para blocos grandes**
   - Adicionar funções completas
   - Modificar classes inteiras
   - Adicionar múltiplas linhas de uma vez

4. **Valide SEMPRE após editar**
   - Use validate_python_syntax('{filepath}')
   - Se inválido, use força write ou rollback

5. **Se precisar adicionar:**
   - **Nova função**: encontre linha vazia apropriada, adicione bloco completo
   - **Novo import**: use search_replace para adicionar na seção de imports
   - **Teste**: adicione no final do arquivo

💡 **ESTRATÉGIA RECOMENDADA para "{goal}":**
"""
            
            # Estratégia baseada no objetivo
            goal_lower = goal.lower()
            
            if 'adicionar' in goal_lower or 'novo' in goal_lower:
                if 'função' in goal_lower or 'método' in goal_lower or 'def' in goal_lower:
                    plan += f"""
a) Identifique onde adicionar (após última função ou antes de testes)
b) Prepare código completo da nova função (com docstring, tipo hints)
c) Se precisa decorator, inclua no mesmo bloco
d) Use edit_lines UMA VEZ com todo o bloco
e) Valide sintaxe
f) Se inválido, corrija com search_replace pontual

**Exemplo de uso correto:**
edit_lines('{filepath}', linha_inserção, linha_inserção, '''
@app.get("/nova_rota")
async def nova_funcao(param: str):
    \"\"\"Docstring\"\"\"
    return {{"result": param.upper()}}
''')
"""
                
                if 'teste' in goal_lower:
                    plan += f"""
a) Adicione import TestClient se necessário (search_replace nos imports)
b) Encontre final do arquivo ou seção de testes
c) Adicione bloco completo do teste (cliente + função de teste)
d) Use edit_lines UMA VEZ com todo o bloco
e) Valide

**Exemplo:**
edit_lines('{filepath}', linha_final, linha_final, '''
# Testes
client = TestClient(app)

def test_funcao():
    response = client.get('/endpoint')
    assert response.status_code == 200
    assert response.json() == {{"expected": "value"}}
''')
"""
            
            elif 'modificar' in goal_lower or 'alterar' in goal_lower:
                plan += f"""
a) Use read_file para ver conteúdo completo
b) Identifique exatamente o que mudar
c) Use search_replace se for mudança pontual
d) Use edit_lines se for mudança de bloco
e) Faça UMA operação de cada vez
f) Valide após cada operação
"""
            
            elif 'corrigir' in goal_lower or 'fix' in goal_lower:
                plan += f"""
a) Valide primeiro para ver qual é o erro
b) Se erro de indentação: use edit_lines no bloco afetado
c) Se erro de sintaxe: use search_replace para correção pontual
d) Se estrutura quebrada: considere force_write_file
e) Valide após correção
"""
            
            plan += f"""

🚨 **CRÍTICO - EVITE ESTES ERROS:**
❌ Editar a mesma linha múltiplas vezes
❌ Fazer edit_lines sem planejar o conteúdo completo
❌ Tentar "consertar" erro com mais edições incrementais
❌ Não validar após mudanças
❌ Continuar editando se validação falhar

✅ **FAÇA ASSIM:**
1. Leia o arquivo (read_file)
2. Planeje a mudança (você está aqui!)
3. Execute UMA operação com bloco completo
4. Valide (validate_python_syntax)
5. Se OK, pronto! Se não, analise erro e corrija UMA vez

🎯 **PRÓXIMO PASSO:**
Use read_file('{filepath}') para ver conteúdo completo e planejar edição exata.
"""
            
            return plan
        
        except Exception as e:
            return f"✗ Erro ao planejar mudanças: {e}"
    
    def _analyze_file_structure(self, filepath: str):
        """
        Analisa estrutura de um arquivo Python.
        Retorna dicionário com seções identificadas.
        """
        file_path = self.workspace / filepath
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        structure = {
            'imports': [],
            'constants': [],
            'classes': [],
            'functions': [],
            'routes': [],
            'tests': [],
            'main_block': None,
            'total_lines': len(lines)
        }
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Imports
            if stripped.startswith(('import ', 'from ')):
                structure['imports'].append(i)
            
            # Constantes (ALL_CAPS no nível do módulo)
            elif stripped and '=' in stripped and not stripped.startswith(('def ', 'class ', '@', '#')):
                parts = stripped.split('=')
                if parts[0].strip().isupper():
                    structure['constants'].append(i)
            
            # Classes
            elif stripped.startswith('class '):
                structure['classes'].append(i)
            
            # Funções/rotas
            elif stripped.startswith('def ') or (i > 1 and lines[i-2].strip().startswith('@')):
                if 'test' in stripped.lower():
                    structure['tests'].append(i)
                elif any(dec in ''.join(lines[max(0,i-5):i]) for dec in ['@app.', '@router.', '@get', '@post']):
                    structure['routes'].append(i)
                else:
                    structure['functions'].append(i)
            
            # Main block
            elif 'if __name__' in stripped:
                structure['main_block'] = i
        
        return structure
    
    def _tool_suggest_insertion(self, filepath: str, code_type: str, description: str = "") -> str:
        """
        🆕 FERRAMENTA CRÍTICA DE POSICIONAMENTO
        
        Sugere ONDE inserir código seguindo boas práticas Python.
        """
        try:
            file_path = self.workspace / filepath
            
            if not file_path.exists():
                return f"❌ Arquivo {filepath} não existe"
            
            structure = self._analyze_file_structure(filepath)
            
            suggestion = f"""
📍 **SUGESTÃO DE POSICIONAMENTO** - {filepath}

🎯 **O QUE VOCÊ QUER ADICIONAR:**
Tipo: {code_type}
Descrição: {description}

📊 **ESTRUTURA ATUAL DO ARQUIVO:**
- Imports: {len(structure['imports'])} (linhas: {structure['imports'][:5] if structure['imports'] else 'nenhum'})
- Constantes: {len(structure['constants'])} (linhas: {structure['constants'][:5] if structure['constants'] else 'nenhum'})
- Classes: {len(structure['classes'])} (linhas: {structure['classes'][:5] if structure['classes'] else 'nenhum'})
- Funções: {len(structure['functions'])} (linhas: {structure['functions'][:5] if structure['functions'] else 'nenhum'})
- Rotas: {len(structure['routes'])} (linhas: {structure['routes'][:5] if structure['routes'] else 'nenhum'})
- Testes: {len(structure['tests'])} (linhas: {structure['tests'][:5] if structure['tests'] else 'nenhum'})
- Main block: {'Sim (linha ' + str(structure['main_block']) + ')' if structure['main_block'] else 'Não'}
- Total de linhas: {structure['total_lines']}

"""
            
            # Sugere linha baseada no tipo de código
            if code_type == 'import':
                if structure['imports']:
                    last_import = max(structure['imports'])
                    suggested_line = last_import
                    suggestion += f"""
✅ **LINHA SUGERIDA: {suggested_line}**

**RAZÃO:** Adicionar após último import (linha {last_import})

**AÇÃO:**
edit_lines('{filepath}', {suggested_line}, {suggested_line}, 'import ou from ...')
"""
                else:
                    suggestion += f"""
✅ **LINHA SUGERIDA: 1**

**RAZÃO:** Nenhum import ainda, adicionar no início do arquivo

**AÇÃO:**
insert_lines('{filepath}', after_line=0, 'import ou from ...')
"""
            
            elif code_type in ['function', 'route']:
                # Rotas/funções devem vir ANTES dos testes
                if structure['tests']:
                    first_test = min(structure['tests'])
                    # Linha antes dos testes (segura)
                    suggested_line = max(first_test - 1, 1)
                    suggestion += f"""
✅ **LINHA SUGERIDA: {suggested_line}** (ANTES dos testes)

**RAZÃO:** Testes começam na linha {first_test}. Funções/rotas devem vir ANTES.
**Total de linhas:** {structure['total_lines']}

⚠️ **IMPORTANTE:** O código atual pode estar desorganizado!

**ORDEM CORRETA:**
1. Imports
2. Constantes
3. App/Router initialization
4. Rotas/Funções
5. Testes  ← você está aqui
6. Main block

**AÇÃO:**
edit_lines('{filepath}', {suggested_line}, {suggested_line}, '''
@app.get("/rota")
async def funcao():
    return resultado
''')
"""
                elif structure['routes'] or structure['functions']:
                    last_func = max((structure['routes'] or []) + (structure['functions'] or []))
                    # Sugere linha segura (não além do arquivo)
                    suggested_line = min(last_func + 3, structure['total_lines'] + 1)
                    
                    suggestion += f"""
✅ **LINHA SUGERIDA: {suggested_line}** (após última função)

**RAZÃO:** Última função/rota está na linha {last_func}
**Total de linhas:** {structure['total_lines']}

**AÇÃO:**
edit_lines('{filepath}', {suggested_line}, {suggested_line}, '''

@app.get("/rota")
async def funcao():
    return resultado
''')

⚠️ **IMPORTANTE:** Arquivo tem {structure['total_lines']} linhas. Você pode inserir até linha {structure['total_lines'] + 1}.
"""
                else:
                    # Após imports/constantes
                    if structure['imports']:
                        suggested_line = min(max(structure['imports']) + 2, structure['total_lines'] + 1)
                    else:
                        suggested_line = 1
                    suggestion += f"""
✅ **LINHA SUGERIDA: {suggested_line}**

**RAZÃO:** Primeira função/rota do arquivo
**Total de linhas:** {structure['total_lines']}

**AÇÃO:**
edit_lines('{filepath}', {suggested_line}, {suggested_line}, '''

@app.get("/rota")
async def funcao():
    return resultado
''')

⚠️ Arquivo tem {structure['total_lines']} linhas. Linha sugerida é segura.
"""
            
            elif code_type == 'test':
                # Testes devem vir APÓS as funções, ANTES do main block
                if structure['main_block']:
                    suggested_line = min(structure['main_block'] - 1, structure['total_lines'] + 1)
                    suggestion += f"""
✅ **LINHA SUGERIDA: {suggested_line}** (ANTES do main block)

**RAZÃO:** Main block está na linha {structure['main_block']}. Testes vêm antes.

**AÇÃO:**
edit_lines('{filepath}', {suggested_line}, {suggested_line}, '''

def test_funcao():
    # teste
    assert resultado == esperado
''')
"""
                elif structure['tests']:
                    last_test = max(structure['tests'])
                    suggested_line = min(last_test + 3, structure['total_lines'] + 1)
                    suggestion += f"""
✅ **LINHA SUGERIDA: {suggested_line}** (após último teste)

**RAZÃO:** Último teste está na linha {last_test}
**Total de linhas:** {structure['total_lines']}

**AÇÃO:**
edit_lines('{filepath}', {suggested_line}, {suggested_line}, '''

def test_novo():
    # teste
    assert resultado == esperado
''')
"""
                else:
                    # Final do arquivo (seguro)
                    suggested_line = structure['total_lines'] + 1
                    suggestion += f"""
✅ **LINHA SUGERIDA: {suggested_line}** (final do arquivo)

**RAZÃO:** Primeiro teste, adicionar no final
**Arquivo tem:** {structure['total_lines']} linhas

**AÇÃO:**
edit_lines('{filepath}', {suggested_line}, {suggested_line}, '''

# Testes
client = TestClient(app)

def test_funcao():
    response = client.get('/endpoint')
    assert response.status_code == 200
''')
"""
            
            elif code_type == 'main_block':
                suggested_line = structure['total_lines'] + 1
                suggestion += f"""
✅ **LINHA SUGERIDA: {suggested_line}** (final do arquivo)

**RAZÃO:** Main block deve ser SEMPRE o último elemento
**Arquivo tem:** {structure['total_lines']} linhas

**AÇÃO:**
edit_lines('{filepath}', {suggested_line}, {suggested_line}, '''

if __name__ == "__main__":
    # código principal
''')
"""
            
            else:
                suggestion += f"\n⚠️ Tipo de código '{code_type}' não reconhecido. Use: import, function, route, test, main_block"
            
            suggestion += f"""

📚 **ORDEM CORRETA PYTHON (PEP 8):**
1. **Docstring do módulo** (se houver)
2. **Imports** (stdlib → third-party → local)
3. **Constantes do módulo** (ALL_CAPS)
4. **Classes**
5. **Funções/Rotas**
6. **Código de teste** (ou arquivo separado)
7. **Main block** (if __name__ == "__main__")

⚠️ **NUNCA coloque:**
- Testes ANTES de funções
- Main block ANTES de testes
- Funções DEPOIS de testes
- Decorators separados de suas funções
"""
            
            return suggestion
        
        except Exception as e:
            return f"✗ Erro ao sugerir inserção: {e}"
    
    def _tool_validate_organization(self, filepath: str) -> str:
        """
        Valida organização do código Python.
        """
        try:
            structure = self._analyze_file_structure(filepath)
            
            problems = []
            warnings = []
            
            # Verifica ordem dos elementos
            all_elements = []
            for imp in structure['imports']:
                all_elements.append(('import', imp))
            for const in structure['constants']:
                all_elements.append(('constant', const))
            for cls in structure['classes']:
                all_elements.append(('class', cls))
            for func in structure['functions']:
                all_elements.append(('function', func))
            for route in structure['routes']:
                all_elements.append(('route', route))
            for test in structure['tests']:
                all_elements.append(('test', test))
            if structure['main_block']:
                all_elements.append(('main', structure['main_block']))
            
            all_elements.sort(key=lambda x: x[1])
            
            # Ordem esperada
            expected_order = ['import', 'constant', 'class', 'function', 'route', 'test', 'main']
            
            # Verifica violações
            last_type_index = -1
            for elem_type, line_num in all_elements:
                current_index = expected_order.index(elem_type) if elem_type in expected_order else 999
                if current_index < last_type_index:
                    problems.append(f"❌ Linha {line_num}: {elem_type} está APÓS elemento que deveria vir depois")
                last_type_index = max(last_type_index, current_index)
            
            # Validações específicas
            if structure['tests'] and structure['routes']:
                first_test = min(structure['tests'])
                last_route = max(structure['routes'])
                if first_test < last_route:
                    problems.append(f"❌ CRÍTICO: Teste (linha {first_test}) está ANTES de rota (linha {last_route})!")
            
            if structure['main_block'] and (structure['tests'] or structure['routes']):
                main_line = structure['main_block']
                last_test = max(structure['tests']) if structure['tests'] else 0
                last_route = max(structure['routes']) if structure['routes'] else 0
                if main_line < max(last_test, last_route):
                    problems.append(f"❌ Main block (linha {main_line}) está ANTES de código funcional!")
            
            # Monta resposta
            if not problems and not warnings:
                return f"✅ ORGANIZAÇÃO EXCELENTE: {filepath} está bem estruturado!\n\nSegue boas práticas Python (PEP 8)."
            else:
                report = f"⚠️ PROBLEMAS DE ORGANIZAÇÃO DETECTADOS: {filepath}\n\n"
                
                if problems:
                    report += "🔴 **PROBLEMAS CRÍTICOS:**\n"
                    for p in problems:
                        report += f"{p}\n"
                
                if warnings:
                    report += "\n💛 **AVISOS:**\n"
                    for w in warnings:
                        report += f"{w}\n"
                
                report += f"""

📚 **ORDEM CORRETA:**
1. Imports
2. Constantes
3. Classes
4. Funções/Rotas
5. Testes
6. Main block

🔧 **RECOMENDAÇÃO:**
Use suggest_insertion_point antes de adicionar código para garantir posicionamento correto.
"""
                return report
        
        except Exception as e:
            return f"✗ Erro ao validar organização: {e}"
    
    def _tool_validate_python(self, filepath: str) -> str:
        """
        Valida sintaxe Python de um arquivo.
        CRÍTICO para detectar quando edições quebraram o código.
        """
        try:
            file_path = self.workspace / filepath
            
            if not file_path.exists():
                return f"❌ Arquivo {filepath} não existe"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Tenta compilar o código
            try:
                compile(content, filepath, 'exec')
                return f"✅ SINTAXE VÁLIDA: {filepath} está correto!\n\nO arquivo tem Python válido e pode ser executado."
            
            except SyntaxError as e:
                error_msg = (
                    f"❌ SINTAXE INVÁLIDA: {filepath}\n\n"
                    f"**Erro:** {e.msg}\n"
                    f"**Linha:** {e.lineno}\n"
                    f"**Coluna:** {e.offset}\n"
                    f"**Texto:** {e.text}\n\n"
                    f"🔧 **AÇÃO NECESSÁRIA:**\n"
                    f"1. Leia o arquivo com read_file para ver o estado atual\n"
                    f"2. Corrija o erro na linha {e.lineno}\n"
                    f"3. Use search_replace ou edit_lines para correção\n"
                    f"4. Valide novamente\n\n"
                    f"⚠️ **DICA:** Se o arquivo está muito quebrado, considere:\n"
                    f"   - Usar um backup: ls -1 {filepath}.*.backup | tail -1\n"
                    f"   - Fazer force_write_file com versão corrigida"
                )
                return error_msg
            
            except IndentationError as e:
                return (
                    f"❌ ERRO DE INDENTAÇÃO: {filepath}\n\n"
                    f"**Linha:** {e.lineno}\n"
                    f"**Erro:** {e.msg}\n\n"
                    f"Problema comum após edit_lines.\n"
                    f"Use edit_lines para corrigir a indentação do bloco afetado."
                )
        
        except Exception as e:
            return f"✗ Erro ao validar: {e}"
    
    def _tool_check_file_and_suggest(self, filepath: str, intended_action: str) -> str:
        """
        Ferramenta inteligente que verifica arquivo e sugere melhor ação.
        
        Ajuda o agente a decidir se deve:
        - Criar arquivo novo
        - Editar arquivo existente
        - Usar outro nome
        
        MELHORIA: Detecta conflitos semânticos (ex: arquivo de teste vs aplicação real)
        """
        try:
            file_path = self.workspace / filepath
            
            # Caso 1: Arquivo NÃO existe - pode criar
            if not file_path.exists():
                return (
                    f"✅ ARQUIVO NÃO EXISTE: '{filepath}'\n\n"
                    f"➡️ AÇÃO RECOMENDADA: **CRIAR ARQUIVO NOVO**\n\n"
                    f"Use: write_file('{filepath}', conteudo)\n\n"
                    f"Você pode criar este arquivo com segurança.\n"
                    f"Intenção: {intended_action}"
                )
            
            # Caso 2: Arquivo existe - precisa decidir
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            lines_count = len(current_content.splitlines())
            chars_count = len(current_content)
            
            # 🆕 ANÁLISE SEMÂNTICA: Detecta conflitos de propósito
            conflict_detected = False
            conflict_reason = ""
            suggested_alternative = ""
            
            # Detecção 1: Arquivo é um script de teste/demo do próprio agent
            if any(indicator in current_content.lower() for indicator in [
                'modernaiaagent', 'execute_task', 'code_agent', 
                'agent.execute', 'from modern_ai_agent'
            ]):
                conflict_detected = True
                conflict_reason = (
                    "Este arquivo é um SCRIPT DE TESTE/DEMO do próprio Modern AI Agent!\n"
                    "   Não é uma aplicação real, é código para testar o agente."
                )
                # Sugere alternativas baseadas na intenção
                if 'fastapi' in intended_action.lower():
                    suggested_alternative = "fastapi_app.py ou main.py ou server.py"
                elif 'flask' in intended_action.lower():
                    suggested_alternative = "flask_app.py ou server.py"
                elif 'django' in intended_action.lower():
                    suggested_alternative = "manage.py (Django usa este nome)"
                else:
                    suggested_alternative = f"main.py ou {filepath.replace('.py', '_app.py')}"
            
            # Detecção 2: Arquivo tem propósito diferente do que você quer criar
            elif 'fastapi' in intended_action.lower() and 'fastapi' not in current_content.lower():
                conflict_detected = True
                conflict_reason = (
                    "Arquivo existe mas NÃO é uma aplicação FastAPI.\n"
                    f"   Conteúdo atual parece ser: {self._guess_file_purpose(current_content)}"
                )
                suggested_alternative = "fastapi_app.py ou main.py"
            
            elif 'flask' in intended_action.lower() and 'flask' not in current_content.lower():
                conflict_detected = True
                conflict_reason = (
                    "Arquivo existe mas NÃO é uma aplicação Flask.\n"
                    f"   Conteúdo atual parece ser: {self._guess_file_purpose(current_content)}"
                )
                suggested_alternative = "flask_app.py ou server.py"
            
            # Análise do arquivo existente
            file_info = (
                f"⚠️ ARQUIVO JÁ EXISTE: '{filepath}'\n\n"
                f"📊 Informações do arquivo atual:\n"
                f"- Linhas: {lines_count}\n"
                f"- Caracteres: {chars_count}\n"
                f"- Primeiras linhas:\n"
            )
            
            # Mostra preview (primeiras 5 linhas)
            preview_lines = current_content.splitlines()[:5]
            for i, line in enumerate(preview_lines, 1):
                file_info += f"  {i}| {line[:80]}\n"
            
            if lines_count > 5:
                file_info += f"  ... (+{lines_count - 5} linhas)\n"
            
            # Decisão baseada na intenção
            action_lower = intended_action.lower()
            
            # Se quer criar algo do zero (indica que talvez não saiba que existe)
            if any(word in action_lower for word in ['criar', 'create', 'novo', 'new']):
                file_info += f"\n🤔 ANÁLISE DA INTENÇÃO: '{intended_action}'\n\n"
                file_info += "Você quer CRIAR, mas o arquivo JÁ EXISTE!\n\n"
                
                # 🆕 SE DETECTOU CONFLITO SEMÂNTICO - Sugere FORTEMENTE usar outro nome
                if conflict_detected:
                    file_info += (
                        f"🔴 **CONFLITO DETECTADO!**\n\n"
                        f"❌ {conflict_reason}\n\n"
                        f"➡️ **AÇÃO RECOMENDADA: USE OUTRO NOME DE ARQUIVO**\n\n"
                        f"🎯 **SUGESTÕES DE NOMES:**\n"
                        f"   - {suggested_alternative}\n\n"
                        f"💡 **FLUXO RECOMENDADO:**\n"
                        f"   1. Escolha um dos nomes sugeridos acima\n"
                        f"   2. Use write_file('<nome_escolhido>', conteudo)\n"
                        f"   3. Mantenha o '{filepath}' original intacto\n\n"
                        f"⚠️ **NÃO EDITE este arquivo** - ele tem propósito diferente!\n"
                        f"⚠️ **NÃO SOBRESCREVA** - você perderia código importante!"
                    )
                else:
                    # Sem conflito - oferece as 3 opções normais
                    file_info += (
                        f"➡️ VOCÊ TEM 3 OPÇÕES:\n\n"
                        f"**OPÇÃO 1 (RECOMENDADO): EDITAR O ARQUIVO EXISTENTE**\n"
                        f"   Se o arquivo já tem conteúdo relacionado, melhor EDITAR:\n"
                        f"   - Para pequenas mudanças: use search_replace('{filepath}', texto_antigo, texto_novo)\n"
                        f"   - Para adicionar linhas: use edit_lines('{filepath}', linha_inicio, linha_fim, novo_conteudo)\n"
                        f"   - Para ler e analisar primeiro: use read_file('{filepath}')\n\n"
                        f"**OPÇÃO 2: USAR NOME DIFERENTE**\n"
                        f"   Crie com outro nome:\n"
                        f"   - {filepath.replace('.', '_v2.')}\n"
                        f"   - {filepath.replace('.', '_new.')}\n"
                        f"   - exemplo_{filepath}\n\n"
                        f"**OPÇÃO 3 (USE COM CAUTELA): SOBRESCREVER**\n"
                        f"   Apenas se tiver CERTEZA que quer substituir completamente:\n"
                        f"   - use force_write_file('{filepath}', novo_conteudo, motivo='explicação clara')\n\n"
                        f"💡 **RECOMENDAÇÃO**: Leia o arquivo primeiro com read_file('{filepath}') para ver o que já tem!"
                    )
            
            # Se quer modificar/editar (indica que sabe que existe)
            elif any(word in action_lower for word in ['modificar', 'editar', 'alterar', 'mudar', 'adicionar', 'corrigir', 'fix', 'update']):
                file_info += (
                    f"\n✅ ÓTIMO! Você quer MODIFICAR arquivo existente.\n\n"
                    f"Intenção: {intended_action}\n\n"
                    f"➡️ AÇÃO RECOMENDADA: **EDITAR ARQUIVO EXISTENTE**\n\n"
                    f"**PASSO 1:** Leia o arquivo para entender o conteúdo\n"
                    f"   read_file('{filepath}')\n\n"
                    f"**PASSO 2:** Escolha a ferramenta de edição apropriada:\n\n"
                    f"   A) **search_replace** - Para substituir texto específico\n"
                    f"      search_replace('{filepath}', 'texto_antigo', 'texto_novo')\n"
                    f"      Exemplo: trocar nome de função, atualizar valor\n\n"
                    f"   B) **edit_lines** - Para editar linhas específicas\n"
                    f"      edit_lines('{filepath}', linha_inicio, linha_fim, 'novo_conteudo')\n"
                    f"      Exemplo: modificar uma função, adicionar imports\n\n"
                    f"❌ **NÃO USE write_file** - Isso tentaria recriar o arquivo!\n\n"
                    f"💡 Primeiro: read_file('{filepath}') para ver o conteúdo atual"
                )
            
            else:
                # Intenção não clara
                file_info += (
                    f"\n🤔 Intenção não totalmente clara: '{intended_action}'\n\n"
                    f"➡️ RECOMENDAÇÃO: **LEIA O ARQUIVO PRIMEIRO**\n\n"
                    f"Use: read_file('{filepath}')\n\n"
                    f"Depois de ler, você poderá decidir:\n"
                    f"- Se é para EDITAR: use search_replace ou edit_lines\n"
                    f"- Se é para criar NOVO: use nome diferente\n"
                    f"- Se é para SOBRESCREVER: use force_write_file (com cuidado!)"
                )
            
            return file_info
        
        except Exception as e:
            return f"✗ Erro ao verificar {filepath}: {e}"
    
    def _guess_file_purpose(self, content: str) -> str:
        """
        Tenta adivinhar o propósito de um arquivo baseado no conteúdo.
        Útil para detectar conflitos semânticos.
        """
        content_lower = content.lower()
        
        # Ordem importa - do mais específico para o mais genérico
        if any(indicator in content_lower for indicator in ['modernaiaagent', 'execute_task', 'agent.execute']):
            return "Script de teste do Modern AI Agent"
        elif 'fastapi' in content_lower:
            return "Aplicação FastAPI"
        elif 'flask' in content_lower:
            return "Aplicação Flask"
        elif 'django' in content_lower:
            return "Aplicação Django"
        elif any(indicator in content_lower for indicator in ['unittest', 'pytest', 'test_', 'def test']):
            return "Arquivo de testes"
        elif 'if __name__ == "__main__"' in content_lower:
            return "Script Python executável"
        elif any(indicator in content_lower for indicator in ['class ', 'def ']):
            return "Módulo Python com classes/funções"
        else:
            return "Script/módulo Python genérico"
    
    def _tool_read_file(self, filepath: str) -> str:
        """Lê um arquivo"""
        try:
            content = self.code_agent.read_file(filepath)
            return f"✓ Conteúdo de {filepath}:\n\n{content}"
        except Exception as e:
            return f"✗ Erro ao ler {filepath}: {e}"
    
    def _tool_write_file(self, filepath: str, content: str) -> str:
        """
        Escreve um arquivo COM VERIFICAÇÃO.
        
        IMPORTANTE: Verifica se arquivo existe e AVISA antes de sobrescrever.
        """
        try:
            file_path = self.workspace / filepath
            
            # VERIFICAÇÃO CRÍTICA: Arquivo existe?
            if file_path.exists():
                # Lê conteúdo atual
                with open(file_path, 'r', encoding='utf-8') as f:
                    current_content = f.read()
                
                # Se conteúdo é diferente, é uma sobrescrita!
                if current_content != content:
                    return (
                        f"⚠️ ATENÇÃO: Arquivo '{filepath}' JÁ EXISTE!\n"
                        f"Tamanho atual: {len(current_content)} caracteres\n"
                        f"Novo tamanho: {len(content)} caracteres\n\n"
                        f"❌ OPERAÇÃO BLOQUEADA para segurança.\n\n"
                        f"Se você REALMENTE quer sobrescrever:\n"
                        f"1. Use 'force_write_file' em vez de 'write_file'\n"
                        f"2. Ou delete o arquivo primeiro com comando shell\n"
                        f"3. Ou escolha outro nome de arquivo\n\n"
                        f"💡 SUGESTÃO: Use um nome diferente como '{filepath}.new' ou '{filepath}_v2'"
                    )
                else:
                    return f"ℹ️ Arquivo {filepath} já existe com mesmo conteúdo (nenhuma mudança necessária)"
            
            # Arquivo não existe, pode criar
            self.code_agent.write_file(filepath, content, show_preview=False)
            return f"✓ Arquivo {filepath} CRIADO com sucesso ({len(content)} caracteres)"
        
        except Exception as e:
            return f"✗ Erro ao escrever {filepath}: {e}"
    
    def _tool_force_write_file(self, filepath: str, content: str, reason: str) -> str:
        """
        Sobrescreve arquivo forçadamente (apenas quando intencional).
        
        Args:
            filepath: Arquivo a sobrescrever
            content: Novo conteúdo
            reason: Motivo da sobrescrita (audit trail)
        """
        try:
            file_path = self.workspace / filepath
            
            if not file_path.exists():
                return (
                    f"⚠️ Arquivo '{filepath}' NÃO EXISTE.\n"
                    f"Use 'write_file' normal para criar arquivos novos.\n"
                    f"force_write_file é apenas para sobrescrever arquivos existentes."
                )
            
            # Lê conteúdo atual para logging
            with open(file_path, 'r', encoding='utf-8') as f:
                old_content = f.read()
            
            # Log da operação
            log_msg = (
                f"🔄 SOBRESCRITA FORÇADA\n"
                f"Arquivo: {filepath}\n"
                f"Motivo: {reason}\n"
                f"Tamanho antigo: {len(old_content)} caracteres\n"
                f"Tamanho novo: {len(content)} caracteres\n"
            )
            
            if self.verbose:
                self.console.print(f"[yellow]{log_msg}[/yellow]")
            
            # Cria backup (importante!)
            self.code_agent.create_backup(filepath)
            
            # Sobrescreve
            self.code_agent.write_file(filepath, content, show_preview=False)
            
            return (
                f"✓ Arquivo {filepath} SOBRESCRITO com sucesso\n"
                f"Motivo: {reason}\n"
                f"Backup criado automaticamente\n"
                f"Mudança: {len(old_content)} → {len(content)} caracteres"
            )
        
        except Exception as e:
            return f"✗ Erro ao sobrescrever {filepath}: {e}"
    
    def _tool_search_replace(self, filepath: str, search: str, replace: str) -> str:
        """Busca e substitui"""
        try:
            self.code_agent.search_replace(filepath, search, replace, show_preview=False)
            return f"✓ Substituição em {filepath} concluída"
        except Exception as e:
            return f"✗ Erro na substituição: {e}"
    
    def _tool_insert_lines(self, filepath: str, after_line: int, content: str) -> str:
        """
        🆕 INSERE código APÓS uma linha específica (não substitui nada).
        
        CRÍTICO: Esta ferramenta ADICIONA código novo sem remover existente!
        """
        try:
            # Lê arquivo atual
            file_content = self.code_agent.read_file(filepath)
            lines = file_content.splitlines(keepends=True)
            total_lines = len(lines)
            
            # Validação
            if after_line < 0:
                return (
                    f"❌ FALHA: after_line deve ser >= 0.\n"
                    f"Use after_line=0 para inserir no INÍCIO do arquivo."
                )
            
            if after_line > total_lines:
                return (
                    f"❌ FALHA: after_line={after_line} está além do arquivo!\n"
                    f"Arquivo tem {total_lines} linhas.\n"
                    f"Use after_line <= {total_lines}"
                )
            
            # Garante newline no final
            if content and not content.endswith('\n'):
                content += '\n'
            
            # Insere APÓS a linha especificada
            new_lines = lines[:after_line] + [content] + lines[after_line:]
            new_content_str = ''.join(new_lines)
            
            # Cria backup
            self.code_agent.create_backup(filepath)
            
            # Escreve
            with open(self.workspace / filepath, 'w', encoding='utf-8') as f:
                f.write(new_content_str)
            
            return (
                f"✅ SUCESSO: Código INSERIDO APÓS linha {after_line} em {filepath}\n\n"
                f"O que aconteceu:\n"
                f"- Arquivo tinha {total_lines} linhas\n"
                f"- Código inserido APÓS linha {after_line}\n"
                f"- Arquivo agora tem {len(new_lines)} linhas\n"
                f"- Backup criado\n\n"
                f"⚠️ Nenhum código existente foi REMOVIDO - apenas ADICIONADO!"
            )
        
        except Exception as e:
            return f"❌ ERRO ao inserir linhas: {e}"
    
    def _tool_edit_lines(self, filepath: str, start_line: int, end_line: int, new_content: str) -> str:
        """
        Edita/SUBSTITUI linhas de um arquivo.
        
        ⚠️ ATENÇÃO: Esta ferramenta REMOVE linhas de start_line até end_line
        e SUBSTITUI pelo novo conteúdo!
        
        Use insert_lines se quiser ADICIONAR sem remover!
        """
        try:
            # Verifica linhas antes de tentar editar
            content = self.code_agent.read_file(filepath)
            total_lines = len(content.splitlines())
            
            # Validação ANTES de chamar edit_lines
            if start_line < 1 or end_line < 1:
                return (
                    f"❌ FALHA: Números de linha inválidos (start={start_line}, end={end_line}).\n"
                    f"Linhas devem ser >= 1.\n\n"
                    f"⚠️ AÇÃO NECESSÁRIA: Corrija os números de linha e tente novamente."
                )
            
            if start_line > total_lines:
                return (
                    f"❌ FALHA CRÍTICA: Linha {start_line} está ALÉM do arquivo!\n\n"
                    f"Arquivo '{filepath}' tem apenas {total_lines} linhas.\n"
                    f"Você tentou inserir na linha {start_line}.\n\n"
                    f"⚠️ AÇÃO NECESSÁRIA:\n"
                    f"1. Use read_file('{filepath}') para ver o conteúdo atual\n"
                    f"2. Para adicionar no FINAL: use linha {total_lines} ou {total_lines + 1}\n"
                    f"3. Para adicionar APÓS última linha: use linha {total_lines + 1}\n"
                    f"4. NUNCA tente adicionar em linha > {total_lines + 1}\n\n"
                    f"💡 DICA: Arquivo com {total_lines} linhas aceita inserção até linha {total_lines + 1}"
                )
            
            if end_line > total_lines:
                return (
                    f"❌ FALHA: Linha final {end_line} está além do arquivo (tem {total_lines} linhas).\n"
                    f"Use linha final <= {total_lines}"
                )
            
            # Tenta editar
            success = self.code_agent.edit_lines(filepath, start_line, end_line, new_content, show_preview=False)
            
            if not success:
                return (
                    f"❌ FALHA: edit_lines retornou False para {filepath} linhas {start_line}-{end_line}.\n"
                    f"Verifique os parâmetros e tente novamente."
                )
            
            return f"✓ Linhas {start_line}-{end_line} de {filepath} editadas com SUCESSO"
        
        except Exception as e:
            return (
                f"❌ ERRO FATAL ao editar {filepath}:\n"
                f"Tipo: {type(e).__name__}\n"
                f"Mensagem: {str(e)}\n\n"
                f"Arquivo pode estar corrompido ou inacessível."
            )
    
    def _tool_delete_lines(
        self,
        filepath: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        line_indices: Optional[List[int]] = None
    ) -> str:
        """
        🗑️ Remove linhas específicas de um arquivo.
        
        Suporta dois modos:
        1. Range: start_line e end_line (1-indexed, inclusivo)
        2. Índices específicos: line_indices (0-indexed, array)
        
        Exemplos:
        - delete_lines('file.py', start_line=5, end_line=10)  # Remove linhas 5-10
        - delete_lines('file.py', line_indices=[0, 10, 23])  # Remove linhas 1, 11, 24
        """
        try:
            # Validação de parâmetros
            if start_line is None and end_line is None and line_indices is None:
                return (
                    "❌ FALHA: Deve fornecer start_line/end_line OU line_indices.\n\n"
                    "Exemplos:\n"
                    "- Range: delete_lines('file.py', start_line=5, end_line=10)\n"
                    "- Índices: delete_lines('file.py', line_indices=[0, 10, 23])"
                )
            
            if (start_line is not None or end_line is not None) and line_indices is not None:
                return (
                    "❌ FALHA: Use range (start_line/end_line) OU line_indices, não ambos.\n\n"
                    "Escolha um modo:\n"
                    "- Range: delete_lines('file.py', start_line=5, end_line=10)\n"
                    "- Índices: delete_lines('file.py', line_indices=[0, 10, 23])"
                )
            
            # Valida range se fornecido
            if start_line is not None or end_line is not None:
                if start_line is None or end_line is None:
                    return (
                        "❌ FALHA: start_line e end_line são obrigatórios no modo range.\n"
                        "Use: delete_lines('file.py', start_line=5, end_line=10)"
                    )
                
                if start_line < 1 or end_line < 1:
                    return (
                        f"❌ FALHA: Números de linha inválidos (start={start_line}, end={end_line}).\n"
                        f"Linhas devem ser >= 1."
                    )
                
                if start_line > end_line:
                    return (
                        f"❌ FALHA: start_line ({start_line}) maior que end_line ({end_line}).\n"
                        f"start_line deve ser <= end_line."
                    )
            
            # Verifica arquivo antes de tentar deletar
            content = self.code_agent.read_file(filepath)
            total_lines = len(content.splitlines())
            
            # Valida range contra arquivo
            if start_line is not None and end_line is not None:
                if start_line > total_lines:
                    return (
                        f"❌ FALHA: Linha inicial {start_line} está além do arquivo!\n"
                        f"Arquivo '{filepath}' tem apenas {total_lines} linhas.\n"
                        f"Use start_line <= {total_lines}"
                    )
                
                if end_line > total_lines:
                    return (
                        f"❌ FALHA: Linha final {end_line} está além do arquivo!\n"
                        f"Arquivo '{filepath}' tem apenas {total_lines} linhas.\n"
                        f"Use end_line <= {total_lines}"
                    )
            
            # Valida índices contra arquivo
            if line_indices is not None:
                for idx in line_indices:
                    if idx < 0:
                        return (
                            f"❌ FALHA: Índice {idx} inválido (deve ser >= 0).\n"
                            f"Índices são 0-indexed (0 = primeira linha)."
                        )
                    if idx >= total_lines:
                        return (
                            f"❌ FALHA: Índice {idx} está além do arquivo!\n"
                            f"Arquivo '{filepath}' tem apenas {total_lines} linhas.\n"
                            f"Índices válidos: 0 a {total_lines - 1} (linhas 1 a {total_lines})"
                        )
            
            # Executa deleção
            success = self.code_agent.delete_lines(
                filepath,
                start_line=start_line,
                end_line=end_line,
                line_indices=line_indices,
                show_preview=False
            )
            
            if not success:
                return (
                    f"❌ FALHA: delete_lines retornou False para {filepath}.\n"
                    f"Verifique os parâmetros e tente novamente."
                )
            
            # Mensagem de sucesso detalhada
            if line_indices is not None:
                line_nums = [idx + 1 for idx in sorted(line_indices)]  # Converter para 1-indexed
                if len(line_nums) == 1:
                    msg = f"✓ Linha {line_nums[0]} de {filepath} removida com SUCESSO"
                else:
                    msg = f"✓ Linhas {line_nums} de {filepath} removidas com SUCESSO"
            else:
                msg = f"✓ Linhas {start_line}-{end_line} de {filepath} removidas com SUCESSO"
            
            return msg
        
        except Exception as e:
            return (
                f"❌ ERRO FATAL ao deletar linhas de {filepath}:\n"
                f"Tipo: {type(e).__name__}\n"
                f"Mensagem: {str(e)}\n\n"
                f"Arquivo pode estar corrompido ou inacessível."
            )
    
    def _tool_list_files(self, pattern: str = "*") -> str:
        """Lista arquivos"""
        try:
            if "**" in pattern:
                files = list(self.workspace.rglob(pattern.replace("**/", "")))
            else:
                files = list(self.workspace.glob(pattern))
            
            files = [f.relative_to(self.workspace) for f in files if f.is_file()]
            files = [f for f in files if ".code_agent_backups" not in str(f)]
            
            if not files:
                return f"Nenhum arquivo encontrado: {pattern}"
            
            files_list = "\n".join(f"  - {f}" for f in files[:50])
            return f"✓ Arquivos encontrados ({len(files)}):\n{files_list}"
        except Exception as e:
            return f"✗ Erro ao listar: {e}"
    
    def _tool_show_file(self, filepath: str) -> str:
        """Mostra arquivo"""
        try:
            content = self.code_agent.read_file(filepath)
            lines = content.splitlines()
            
            preview = "\n".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines[:30]))
            
            more = f"\n... ({len(lines) - 30} linhas restantes)" if len(lines) > 30 else ""
            
            return f"✓ Preview de {filepath} ({len(lines)} linhas):\n\n{preview}{more}"
        except Exception as e:
            return f"✗ Erro: {e}"
    
    def _tool_run_command(self, command: str, timeout: int = 30) -> str:
        """
        Executa um comando shell único.
        
        Args:
            command: Comando shell a executar
            timeout: Timeout em segundos
            
        Returns:
            Resultado da execução
        """
        # Lista de comandos perigosos bloqueados
        dangerous_commands = [
            'rm -rf', 'mkfs', 'dd', ':(){:|:&};:', 'fork bomb',
            '>(', '/dev/sda', 'mv / ', 'chmod -R 777 /',
            '> /dev/sda', 'wget http', 'curl http'
        ]
        
        # Valida se não contém comandos perigosos
        command_lower = command.lower()
        for dangerous in dangerous_commands:
            if dangerous.lower() in command_lower:
                return f"✗ BLOQUEADO: Comando potencialmente perigoso detectado: '{dangerous}'"
        
        try:
            if self.verbose:
                self.console.print(f"[dim]Executando: {command}[/dim]")
            
            # Executa com timeout no workspace
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Formata saída
            output = []
            output.append(f"✓ Comando executado: {command}")
            output.append(f"Exit code: {result.returncode}")
            
            if result.stdout:
                output.append(f"\nSTDOUT:\n{result.stdout}")
            
            if result.stderr:
                output.append(f"\nSTDERR:\n{result.stderr}")
            
            return "\n".join(output)
        
        except subprocess.TimeoutExpired:
            return f"✗ TIMEOUT: Comando excedeu {timeout}s de execução"
        except Exception as e:
            return f"✗ Erro ao executar comando: {e}"
    
    def _tool_run_script(self, script: str, shell: str = "bash", timeout: int = 60) -> str:
        """
        Executa um script shell completo.
        
        Args:
            script: Script shell (múltiplas linhas)
            shell: Shell a usar (bash, sh, zsh)
            timeout: Timeout em segundos
            
        Returns:
            Resultado da execução
        """
        # Valida shell
        allowed_shells = ['bash', 'sh', 'zsh', 'dash']
        if shell not in allowed_shells:
            return f"✗ Shell não permitido: {shell}. Use: {', '.join(allowed_shells)}"
        
        # Lista de padrões perigosos em scripts
        dangerous_patterns = [
            'rm -rf /', 'rm -rf *', 'mkfs', 'dd if=', 'dd of=/dev',
            ':(){:|:&};:', '> /dev/sda', 'chmod -R 777 /',
            'wget http://', 'curl http://'
        ]
        
        # Valida conteúdo do script
        script_lower = script.lower()
        for dangerous in dangerous_patterns:
            if dangerous.lower() in script_lower:
                return f"✗ BLOQUEADO: Padrão perigoso detectado no script: '{dangerous}'"
        
        try:
            if self.verbose:
                self.console.print(f"[dim]Executando script {shell}...[/dim]")
            
            # Executa script com timeout
            result = subprocess.run(
                [shell, '-c', script],
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Formata saída
            output = []
            output.append(f"✓ Script {shell} executado")
            output.append(f"Exit code: {result.returncode}")
            
            if result.stdout:
                output.append(f"\nSTDOUT:\n{result.stdout}")
            
            if result.stderr:
                output.append(f"\nSTDERR:\n{result.stderr}")
            
            return "\n".join(output)
        
        except subprocess.TimeoutExpired:
            return f"✗ TIMEOUT: Script excedeu {timeout}s de execução"
        except FileNotFoundError:
            return f"✗ Shell não encontrado: {shell}"
        except Exception as e:
            return f"✗ Erro ao executar script: {e}"
    
    def _create_task_summary(
        self,
        task: str,
        messages: List[Dict[str, Any]],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cria um resumo estruturado de uma tarefa executada.
        
        Args:
            task: Tarefa original
            messages: Todas as mensagens da conversa
            result: Resultado da execução
            
        Returns:
            Dicionário com resumo da tarefa
        """
        # Extrai tool calls executados
        tool_calls_executed = []
        for msg in messages:
            if msg.get("role") == "assistant":
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    for tool_call in tool_calls:
                        if isinstance(tool_call, dict):
                            func = tool_call.get("function", {})
                            tool_calls_executed.append({
                                "name": func.get("name"),
                                "arguments": func.get("arguments")
                            })
                        else:
                            # Pode ser objeto com atributos
                            try:
                                tool_calls_executed.append({
                                    "name": getattr(tool_call, "function", {}).name if hasattr(tool_call, "function") else "unknown",
                                    "arguments": getattr(tool_call, "function", {}).arguments if hasattr(tool_call, "function") else {}
                                })
                            except:
                                pass
        
        # Extrai resultados das tools
        tool_results = []
        for msg in messages:
            if msg.get("role") == "tool":
                tool_results.append({
                    "tool_call_id": msg.get("tool_call_id"),
                    "content": msg.get("content", "")[:200]  # Primeiros 200 chars
                })
        
        # Resposta final
        final_response = result.get("final_response", "")
        
        summary = {
            "task_id": self.task_counter,
            "task": task,
            "timestamp": result.get("timestamp"),
            "iterations": result.get("iterations", 0),
            "tool_calls_count": len(tool_calls_executed),
            "tools_used": list(set([tc["name"] for tc in tool_calls_executed if tc["name"]])),
            "success": result.get("success", False),
            "final_response": final_response[:500] if final_response else "",  # Primeiros 500 chars
            "key_actions": tool_calls_executed[:10]  # Primeiras 10 ações
        }
        
        return summary
    
    def _build_context_from_history(self) -> str:
        """
        Constrói contexto a partir do histórico de tarefas anteriores.
        
        Returns:
            String com contexto formatado para incluir no prompt
        """
        if not self.task_summaries and not self.conversation_history:
            return ""
        
        context_parts = []
        
        # Resumo de todas as tarefas anteriores
        if self.task_summaries:
            context_parts.append("📚 **HISTÓRICO DE TAREFAS ANTERIORES:**\n")
            for summary in self.task_summaries[-10:]:  # Últimas 10 tarefas
                context_parts.append(
                    f"\n**Tarefa #{summary['task_id']}:** {summary['task'][:100]}...\n"
                    f"- Status: {'✅ Sucesso' if summary['success'] else '❌ Falhou'}\n"
                    f"- Iterações: {summary['iterations']}\n"
                    f"- Ferramentas usadas: {', '.join(summary['tools_used'][:5])}\n"
                    f"- Resposta: {summary['final_response'][:200]}...\n"
                )
        
        # Detalhes completos das últimas 3 tarefas
        if self.conversation_history:
            context_parts.append("\n\n🔍 **DETALHES DAS ÚLTIMAS TAREFAS:**\n")
            for idx, task_messages in enumerate(self.conversation_history[-3:], 1):
                task_num = len(self.conversation_history) - 3 + idx
                context_parts.append(f"\n**Tarefa #{task_num} - Mensagens completas:**\n")
                
                # Mostra apenas mensagens relevantes (user, assistant, tool results importantes)
                for msg in task_messages[-20:]:  # Últimas 20 mensagens por tarefa
                    role = msg.get("role", "")
                    if role == "user":
                        content = msg.get("content", "")
                        context_parts.append(f"👤 Usuário: {content[:200]}...\n")
                    elif role == "assistant" and msg.get("content"):
                        content = msg.get("content", "")
                        context_parts.append(f"🤖 Assistente: {content[:200]}...\n")
                    elif role == "tool":
                        tool_id = msg.get("tool_call_id", "")
                        content = msg.get("content", "")
                        # Apenas resultados importantes
                        if "SUCESSO" in content or "FALHA" in content or "ERRO" in content:
                            context_parts.append(f"🔧 Tool {tool_id[:8]}...: {content[:150]}...\n")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def execute_task(
        self,
        task: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executa uma tarefa usando o padrão ReAct.
        
        Args:
            task: Descrição da tarefa em linguagem natural
            system_prompt: Prompt de sistema customizado (opcional)
            
        Returns:
            Dicionário com resultado e metadados
        """
        # Incrementa contador de tarefas
        self.task_counter += 1
        
        # 🆕 Log início da tarefa
        self._write_log(f"\n{'─'*80}\n")
        self._write_log(f"📋 TAREFA #{self.task_counter}\n")
        self._write_log(f"{'─'*80}\n")
        self._write_log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self._write_log(f"Tarefa: {task}\n")
        self._write_log(f"{'─'*80}\n\n")
        
        if self.verbose:
            self.console.print(Panel(
                f"[cyan]🤖 Tarefa #{self.task_counter}:[/cyan]\n{task}",
                border_style="cyan",
                box=box.ROUNDED
            ))
        
        # Constrói contexto do histórico
        history_context = self._build_context_from_history()
        
        # Prompt de sistema padrão
        if not system_prompt:
            system_prompt = f"""Você é um assistente especializado em edição de código.

Workspace: {self.workspace}

🚨 **MODO DE OPERAÇÃO: WORKFLOW ESTRUTURADO OBRIGATÓRIO**

Você DEVE seguir um workflow estruturado em 5 FASES. NUNCA pule fases!

**ANTES de começar a executar ferramentas:**
1. Raciocine sobre a tarefa (explique seu entendimento)
2. Liste arquivos existentes
3. Analise conflitos potenciais
4. Leia conteúdo necessário
5. Planeje TUDO antes de executar

**DEPOIS de executar:**
6. Verifique e critique o resultado
7. Ajuste se necessário
8. Se houver execução shell: planeje antes, execute, analise resultado

Veja detalhes completos do workflow abaixo.

---

Você tem acesso a ferramentas para manipular arquivos. Use-as de forma inteligente e SEGURA:

⚠️ **INTERPRETAÇÃO DE CONTEXTO (CRÍTICO - NOVO!):**

**ANTES de implementar, ANALISE o contexto do arquivo:**

1. **Se o arquivo usa FastAPI/Flask/Django:**
   - "adicionar método" = criar ROTA HTTP (@app.get, @app.post, etc.)
   - "adicionar endpoint" = criar ROTA HTTP
   - "testar método" = testar CHAMADA HTTP (não função Python pura)
   - Exemplo: @app.get("/uppercase/{{nome}}") async def uppercase(nome: str)

2. **Se o arquivo é Python puro (sem framework web):**
   - "adicionar método" = criar função Python normal
   - "testar método" = testar função diretamente

3. **Testes em contexto de API:**
   - Use TestClient do FastAPI para testar rotas HTTP
   - Teste o endpoint, não a função diretamente
   - Exemplo: response = client.get('/rota')

4. **Sempre confirme:**
   - Leia o arquivo PRIMEIRO (read_file)
   - Identifique imports (FastAPI? Flask? Django?)
   - Entenda o padrão usado no arquivo
   - Implemente seguindo o mesmo padrão

**FLUXO OBRIGATÓRIO:**
1. read_file - Veja o conteúdo e identifique o contexto
2. Identifique o framework/padrão usado
3. Implemente seguindo esse padrão
4. Para APIs: crie ROTAS HTTP, não funções Python puras

🔴 REGRAS CRÍTICAS DE SEGURANÇA:

1. **🚨 REGRA MAIS IMPORTANTE:**
   **SEMPRE use check_file_and_suggest_action ANTES de criar/modificar qualquer arquivo!**
   
   Esta ferramenta vai:
   - Verificar se arquivo existe
   - Analisar o conteúdo atual (se existir)
   - Sugerir a MELHOR ação (criar, editar, ou usar outro nome)
   - Te orientar sobre qual ferramenta usar
   
   Exemplo:
   ```
   check_file_and_suggest_action('app.py', 'criar aplicação fastapi')
   ```
   
2. **write_file é APENAS para arquivos NOVOS**
   - Se arquivo já existe, write_file será BLOQUEADO
   - Você receberá mensagem dizendo para usar outra ferramenta
   
3. **Para MODIFICAR arquivos existentes, NUNCA use write_file!**
   Use as ferramentas de edição:
   
   **Para ADICIONAR código:**
   - 🆕 **insert_lines** - ADICIONA código APÓS uma linha (não remove nada!)
   - Exemplo: insert_lines('main.py', after_line=8, 'código novo')
   - Insere o código ENTRE linha 8 e 9, mantendo ambas intactas
   
   **Para MODIFICAR código existente:**
   - **search_replace** - Substituir texto específico (melhor para mudanças pontuais)
   - **edit_lines** - SUBSTITUI linhas (REMOVE start_line até end_line e põe novo)
   - ⚠️ edit_lines(5, 7, 'X') REMOVE linhas 5, 6, 7 e põe 'X' no lugar!
   
   **Para LER:**
   - **read_file** - Sempre leia primeiro para entender o conteúdo
   
   ⚠️ **REGRA CRÍTICA:** 
   - Use insert_lines para ADICIONAR código novo (default!)
   - Use edit_lines APENAS para SUBSTITUIR código existente
   - Nunca use edit_lines pensando que vai "adicionar"!
   
4. **🆕 POSICIONAMENTO É OBRIGATÓRIO! (NOVO - CRÍTICO)**
   **ANTES de adicionar qualquer código, SEMPRE use:**
   ```
   suggest_insertion_point('arquivo.py', 'tipo_codigo', 'descrição')
   ```
   
   Tipos: 'import', 'function', 'route', 'test', 'main_block'
   
   Esta ferramenta vai:
   - Analisar estrutura atual do arquivo (imports, funções, testes, etc)
   - Te dizer a LINHA EXATA onde inserir o código
   - Garantir que você siga ordem correta (PEP 8)
   - Prevenir código desorganizado (função depois de teste, etc)
   
   ⚠️ **CRÍTICO:** NUNCA adicione código sem saber ONDE colocar!
   ⚠️ Rotas/Funções devem vir ANTES de Testes!
   ⚠️ Testes devem vir ANTES de Main block!

5. **🆕 PLANEJAMENTO É OBRIGATÓRIO! (NOVO)**
   **ANTES de fazer múltiplas edições, SEMPRE use:**
   ```
   plan_file_changes('arquivo.py', 'objetivo da modificação')
   ```
   
   Esta ferramenta vai:
   - Analisar estrutura atual do arquivo
   - Sugerir estratégia de edição eficiente
   - Prevenir loops de edições linha por linha
   - Te orientar sobre qual abordagem usar
   
   ⚠️ **CRÍTICO:** Se você precisa fazer mais de 1 edit_lines, PLANEJE PRIMEIRO!

6. **🆕 VALIDAÇÃO É OBRIGATÓRIA! (NOVO)**
   **APÓS cada edição em arquivo Python:**
   ```
   validate_python_syntax('arquivo.py')
   validate_code_organization('arquivo.py')  # Verifica se está bem organizado
   ```
   
   - Se VÁLIDO: continue com próxima operação
   - Se INVÁLIDO: PARE e corrija o erro ANTES de continuar
   - Se DESORGANIZADO: corrija posicionamento
   - NÃO faça mais edições se validação falhar!
   - Se muito quebrado, considere usar backup ou force_write_file
   
7. **Se quiser criar arquivo mas nome já existe:**
   - OPÇÃO A (MELHOR): Edite o arquivo existente (se fizer sentido)
   - OPÇÃO B: Use nome diferente (app_v2.py, example_app.py)
   - OPÇÃO C (CUIDADO): Use force_write_file com motivo claro

8. **force_write_file - Use APENAS quando:**
   - Você tem CERTEZA que quer sobrescrever completamente
   - Fornece motivo claro e válido
   - Sabe que o usuário quer substituir o arquivo

🔴 **WORKFLOW OBRIGATÓRIO - SIGA ESTA ORDEM EXATA!**

**FASE 1: RACIOCÍNIO E EXPLORAÇÃO (OBRIGATÓRIO - NUNCA PULE!)**

1. **RACIOCÍNIO PRELIMINAR (OBRIGATÓRIO - PRIMEIRO PASSO!):**
   - ANTES de chamar qualquer ferramenta, use sua RESPOSTA DE TEXTO para:
     - Analisar a tarefa recebida
     - Explicar o que você entendeu que precisa ser feito
     - Identificar que tipo de arquivos serão afetados
     - Pensar em possíveis conflitos ou dependências
     - Listar arquivos que podem existir e precisar verificação
   - Exemplo de resposta:
     ```
     "Entendi que preciso adicionar um método HTTP em main.py que recebe 'nome' e retorna uppercase.
     Como main.py é FastAPI, preciso criar uma ROTA HTTP (@app.get), não uma função Python pura.
     Também preciso criar testes pytest que chamem essa rota HTTP.
     Vou verificar se já existem arquivos de teste que podem conflitar."
     ```
   - ⚠️ NUNCA comece executando ferramentas sem explicar seu raciocínio primeiro!

2. **LISTAR ARQUIVOS EXISTENTES:**
   ```
   list_files()  # OU list_files('padrão*.py') para filtrar
   ```
   - Veja TODOS os arquivos relevantes no workspace
   - Identifique arquivos que podem conflitar
   - Identifique arquivos que precisam ser modificados

3. **ANÁLISE DE CONFLITOS:**
   - Para cada arquivo mencionado na tarefa:
     ```
     check_file_and_suggest_action('arquivo.py', 'intenção')
     ```
   - Identifique arquivos que podem conflitar (mesmo nome, propósito diferente)
   - Identifique arquivos que devem ser alterados
   - **CRÍTICO para testes:**
     - Liste TODOS os arquivos de teste existentes: `list_files('*test*.py')`
     - Verifique se já existe teste para o arquivo que você vai modificar
     - Se existir: edite o teste existente, não crie novo!
     - Se não existir: crie em local apropriado (tests/ ou mesmo diretório)
   - Decida: criar novo, editar existente, ou usar outro nome?

4. **LER CONTEÚDO NECESSÁRIO:**
   ```
   read_file('arquivo1.py')
   read_file('arquivo2.py')
   # Leia TODOS os arquivos que serão afetados!
   ```
   - Entenda o contexto completo
   - Identifique padrões (FastAPI? Flask? Python puro?)
   - Veja estrutura atual (imports, funções, rotas, testes)

**FASE 2: PLANEJAMENTO DETALHADO (OBRIGATÓRIO!)**

5. **GERAR PLANO COMPLETO:**
   ```
   plan_file_changes('arquivo.py', 'objetivo completo')
   ```
   - Agora que você TEM as informações, planeje:
   - Que arquivos criar?
   - Que arquivos modificar?
   - Que linhas inserir/editar/deletar?
   - Em que ordem executar?

6. **PLANEJAR POSICIONAMENTO:**
   Para cada inserção de código:
   ```
   suggest_insertion_point('arquivo.py', 'tipo', 'descrição')
   ```
   - Descubra a LINHA EXATA onde inserir
   - Garanta ordem correta (PEP 8)
   - Planeje TODAS as inserções antes de executar

**FASE 3: EXECUÇÃO (APÓS PLANEJAR TUDO!)**

7. **EXECUTAR MUDANÇAS:**
   - CRIAR arquivos novos: `write_file('novo.py', conteúdo_completo)`
   - ADICIONAR código: `insert_lines('arquivo.py', after_line=X, conteúdo_bloco_completo)`
   - MODIFICAR código: `search_replace()` ou `edit_lines()`
   - DELETAR código: `edit_lines(start, end, '')` ou `search_replace()`
   - ⚠️ SEMPRE use BLOCOS COMPLETOS, nunca linha por linha!
   - ⚠️ Execute na ordem planejada!

**FASE 4: VERIFICAÇÃO E CRÍTICA (OBRIGATÓRIO!)**

8. **VERIFICAR E CRITICAR:**
   ```
   validate_python_syntax('arquivo.py')
   validate_code_organization('arquivo.py')
   read_file('arquivo.py')  # Veja resultado final
   ```
   - Sintaxe está correta?
   - Organização está boa?
   - Código está completo?
   - Segue o padrão do arquivo?
   - Atende o requisito da tarefa?

9. **AJUSTAR SE NECESSÁRIO:**
   - Se validação FALHAR: PARE e corrija!
   - Se código incompleto: complete!
   - Se organização ruim: reorganize!
   - Se não atende requisito: ajuste!
   - Valide novamente após ajustes

**FASE 5: EXECUÇÃO SHELL (SE SOLICITADO)**

10. **SE TAREFA PEDE EXECUÇÃO (teste, script, etc):**
    - ⚠️ ANTES de executar, SEMPRE PLANEJE usando sua RESPOSTA DE TEXTO:
      - Que comando executar? (exato, com flags corretas)
      - Que arquivo de teste usar? (caminho completo)
      - Que resultado esperar? (sucesso? quantos testes passam?)
      - Onde executar? (workspace root? subdiretório?)
      - Exemplo:
        ```
        "Vou executar pytest para testar a rota HTTP criada.
        Comando: pytest tests/test_main.py -v
        Espero: exit code 0, todos os testes passando
        Local: workspace root (/workspaces/super-prompt)"
        ```
    
11. **EXECUTAR COMANDO:**
    ```
    run_command('pytest tests/test_main.py -v', timeout=120)
    # OU
    run_command('python script.py', timeout=60)
    ```
    - Capture output completo (stdout + stderr)
    - Analise exit code (0 = sucesso, != 0 = erro)
    - Analise mensagens de erro (se houver)

12. **ANALISAR RESULTADO (OBRIGATÓRIO!):**
    - Se SUCESSO (exit 0):
      - Verifique se resultado está conforme esperado
      - Se tudo OK: Tarefa concluída! ✅
      - Se resultado inesperado: analise e ajuste
    - Se ERRO (exit != 0):
      - Leia mensagem de erro COMPLETA
      - Identifique problema específico (import? sintaxe? arquivo não encontrado?)
      - Use sua RESPOSTA para explicar o problema
      - Volte para FASE 2 (planejar correção detalhada)
      - Execute correção
      - Execute comando novamente
      - Repita até sucesso ou limite de iterações
    - ⚠️ NUNCA ignore erros! Sempre analise e corrija!

**REGRAS CRÍTICAS:**
- ⚠️ NUNCA execute sem planejar primeiro!
- ⚠️ NUNCA pule a fase de verificação!
- ⚠️ NUNCA continue após erro de validação!
- ⚠️ SEMPRE leia arquivos antes de modificar!
- ⚠️ SEMPRE valide após cada mudança significativa!
- ⚠️ SEMPRE planeje execuções shell antes de executar!

FERRAMENTAS DISPONÍVEIS (17 total):
- check_file_and_suggest_action: 🆕 USE SEMPRE PRIMEIRO! Verifica arquivo e sugere ação
- suggest_insertion_point: 🆕 CRÍTICO! Descobre ONDE inserir código (linha exata)
- plan_file_changes: 🆕 PLANEJE antes de múltiplas edições! Previne loops
- validate_python_syntax: 🆕 VALIDE sintaxe após edições! Detecta erros
- validate_code_organization: 🆕 VALIDE organização! Verifica boas práticas
- insert_lines: 🆕 ADICIONA código APÓS linha (não remove nada!) - USE ESTE!
- read_file: Lê arquivo completo
- write_file: Cria arquivo novo (bloqueia se existe)
- force_write_file: Sobrescreve (USE COM CAUTELA + motivo!)
- search_replace: Modifica texto (substituições pontuais)
- edit_lines: SUBSTITUI linhas (REMOVE e põe novo) - cuidado!
- delete_lines: 🆕 Remove linhas específicas (range ou índices) - NOVO!
- list_files: Lista arquivos do workspace
- show_file: Preview rápido de arquivo
- run_command: Executa comando shell único
- run_script: Executa script shell completo

🚨 **ERROS COMUNS QUE VOCÊ DEVE EVITAR:**

❌ **ERRO 0: Criar função Python quando deveria criar rota HTTP** 🔴 CRÍTICO NOVO!
   Problema: Em arquivo FastAPI, criar "def func()" ao invés de "@app.get('/rota')"
   Exemplo ERRADO:
   ```python
   def uppercase_nome(nome: str):  # ❌ Função Python pura
       return nome.upper()
   ```
   Exemplo CORRETO:
   ```python
   @app.get("/uppercase/{{nome}}")  # ✅ Rota HTTP
   async def uppercase_nome(nome: str):
       return {{"result": nome.upper()}}
   ```
   Solução: 
   - SEMPRE leia arquivo primeiro
   - Se tiver "from fastapi import FastAPI" → criar ROTAS HTTP!
   - Se tiver "from flask import Flask" → criar ROTAS HTTP!
   - Testes devem usar TestClient para chamar API

❌ **ERRO 1: Usar edit_lines para ADICIONAR código** 🔴 CRÍTICO!
   Problema: edit_lines(8, 8, 'novo') SUBSTITUI linha 8, não adiciona!
   Solução: Use insert_lines(filepath, after_line=8, 'novo') para ADICIONAR

❌ **ERRO 2: Adicionar código no lugar errado**
   Problema: Adicionar função DEPOIS de testes, rota DEPOIS de main block
   Solução: SEMPRE use suggest_insertion_point ANTES de insert_lines

❌ **ERRO 3: Edições linha por linha**
   Problema: Fazer insert_lines 20x para adicionar 1 função
   Solução: Use plan_file_changes, prepare bloco completo, execute UMA vez

❌ **ERRO 4: Continuar editando após erro de validação**
   Problema: Arquivo fica inválido, você continua editando e piora
   Solução: PARE quando validate_python_syntax falhar, corrija primeiro

❌ **ERRO 5: Não planejar antes de executar**
   Problema: Começa a editar sem saber o que fazer, cria loops
   Solução: Use plan_file_changes SEMPRE que precisa de múltiplas edições

❌ **ERRO 6: Tentar "consertar" erro com mais edições**
   Problema: Arquivo quebrado, você tenta 10 edit_lines para consertar
   Solução: Se arquivo ficou muito quebrado, use backup ou force_write_file

❌ **ERRO 7: Editar sem ler o conteúdo atual**
   Problema: Você não sabe o estado atual, quebra a estrutura
   Solução: SEMPRE use read_file antes de modificar

✅ **PADRÃO CORRETO:**
1. check_file_and_suggest_action - Verifica se arquivo existe
2. plan_file_changes - Planeja estratégia (se múltiplas edições)
3. read_file - Lê conteúdo atual
4. 🆕 suggest_insertion_point - Descobre ONDE inserir (linha exata!)
5. 🆕 insert_lines - ADICIONA código APÓS linha sugerida (bloco completo!)
   - OU search_replace - Para mudanças pontuais em texto existente
   - OU edit_lines - APENAS para SUBSTITUIR código existente (remove + põe novo)
6. validate_python_syntax - Sintaxe OK?
7. 🆕 validate_code_organization - Organização OK?
8. Se válido: OK! Se não: corrija pontualmente e valide de novo

🎯 **REGRA DE OURO:**
- Para ADICIONAR código novo → use insert_lines
- Para MODIFICAR texto existente → use search_replace
- Para SUBSTITUIR blocos completos → use edit_lines
- NUNCA confunda insert_lines com edit_lines!

IMPORTANTE:
- Sempre liste arquivos primeiro para saber o que existe
- Nunca sobrescreva arquivos importantes sem motivo claro
- Use caminhos relativos ao workspace
- Seja preciso nas modificações
- Explique seu raciocínio (reasoning)
- PLANEJE antes de EXECUTAR
- VALIDE após EDITAR"""
        
        # Adiciona histórico ao system prompt se houver
        if history_context:
            system_prompt = system_prompt + "\n\n" + history_context + "\n\n" + "💡 **USE O HISTÓRICO ACIMA** para entender contexto de tarefas anteriores e evitar repetir ações já executadas."
        
        # Histórico de mensagens
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]
        
        iteration = 0
        total_tool_calls = 0
        current_model = self.default_model  # Começa com modelo padrão
        
        # 🆕 Contadores de tokens
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        
        try:
            while iteration < self.max_iterations:
                iteration += 1
                
                # 🆕 Log iteração
                self._write_log(f"\n{'▸'*40}\n")
                self._write_log(f"🔄 ITERAÇÃO {iteration}/{self.max_iterations}\n")
                self._write_log(f"{'▸'*40}\n")
                self._write_log(f"Modelo: {current_model}\n")
                if self.use_multi_model:
                    complexity = "🧠 COMPLEX" if current_model == self.complex_model else "⚡ SIMPLE"
                    self._write_log(f"Complexidade: {complexity}\n")
                self._write_log(f"\n")
                
                if self.verbose:
                    self.console.print(f"\n[dim]═══ Iteração {iteration}/{self.max_iterations} ═══[/dim]")
                
                # 🆕 Seleção dinâmica de modelo (se multi-model habilitado)
                if self.use_multi_model and self.verbose:
                    model_display = "🧠 " + current_model if current_model == self.complex_model else "⚡ " + current_model
                    self.console.print(f"[dim]Modelo: {model_display}[/dim]")
                
                # Chamada para OpenAI com function calling
                response = self.client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    tools=self.tools_schema,
                    tool_choice="auto"  # Deixa o modelo decidir
                )
                
                message = response.choices[0].message
                
                # 🆕 Captura uso de tokens
                if hasattr(response, 'usage') and response.usage:
                    prompt_tokens = response.usage.prompt_tokens
                    completion_tokens = response.usage.completion_tokens
                    tokens_used = response.usage.total_tokens
                    
                    total_prompt_tokens += prompt_tokens
                    total_completion_tokens += completion_tokens
                    total_tokens += tokens_used
                    
                    # Log tokens desta iteração
                    self._write_log(f"📊 Tokens (iteração {iteration}):\n")
                    self._write_log(f"   Prompt (input): {prompt_tokens:,}\n")
                    self._write_log(f"   Completion (output): {completion_tokens:,}\n")
                    self._write_log(f"   Total: {tokens_used:,}\n")
                    self._write_log(f"   Modelo: {current_model}\n\n")
                
                # Adiciona resposta ao histórico
                messages.append(message.model_dump())
                
                # Verifica se terminou (sem tool calls)
                if not message.tool_calls:
                    final_response = message.content
                    
                    # 🆕 Log resposta final
                    self._write_log(f"✅ RESPOSTA FINAL DO ASSISTENTE:\n")
                    self._write_log(f"{'-'*80}\n")
                    self._write_log(f"{final_response}\n")
                    self._write_log(f"{'-'*80}\n\n")
                    
                    if self.verbose:
                        self.console.print(Panel(
                            f"[green]✓ Tarefa concluída![/green]\n\n{final_response}",
                            border_style="green",
                            title="Resultado"
                        ))
                    
                    # 🆕 Salva memória da tarefa
                    result = {
                        "success": True,
                        "response": final_response,
                        "final_response": final_response,
                        "iterations": iteration,
                        "tool_calls": total_tool_calls,
                        "messages": messages,
                        "timestamp": datetime.now().isoformat(),
                        # 🆕 Tokens usage
                        "tokens": {
                            "prompt_tokens": total_prompt_tokens,
                            "completion_tokens": total_completion_tokens,
                            "total_tokens": total_tokens
                        }
                    }
                    
                    # Cria resumo da tarefa
                    summary = self._create_task_summary(task, messages, result)
                    self.task_summaries.append(summary)
                    
                    # Salva mensagens completas (mantém apenas últimas 3)
                    self.conversation_history.append(messages.copy())
                    if len(self.conversation_history) > self.max_history_tasks:
                        self.conversation_history.pop(0)  # Remove a mais antiga
                    
                    # 🆕 Log sumário final
                    self._write_log(f"\n{'='*80}\n")
                    self._write_log(f"📊 SUMÁRIO DA TAREFA #{self.task_counter}\n")
                    self._write_log(f"{'='*80}\n")
                    self._write_log(f"Status: ✅ CONCLUÍDA\n")
                    self._write_log(f"Iterações: {iteration}\n")
                    self._write_log(f"Tool calls: {total_tool_calls}\n")
                    self._write_log(f"Tokens (Request): {total_prompt_tokens:,}\n")
                    self._write_log(f"Tokens (Response): {total_completion_tokens:,}\n")
                    self._write_log(f"Tokens (Total): {total_tokens:,}\n")
                    self._write_log(f"Tempo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    self._write_log(f"{'='*80}\n")
                    
                    # 🆕 Mostra tokens no console se verbose
                    if self.verbose:
                        self.console.print(f"\n[cyan]📊 Uso de Tokens:[/cyan]")
                        self.console.print(f"[dim]  Request (input): {total_prompt_tokens:,}[/dim]")
                        self.console.print(f"[dim]  Response (output): {total_completion_tokens:,}[/dim]")
                        self.console.print(f"[dim]  Total: {total_tokens:,}[/dim]")
                    
                    return result
                
                # Executa tool calls
                for tool_call in message.tool_calls:
                    total_tool_calls += 1
                    
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # 🆕 Log tool call
                    self._write_log(f"🔧 TOOL #{total_tool_calls}: {tool_name}\n")
                    tool_complexity = self.tool_complexity.get(tool_name, "simple")
                    complexity_icon = "🧠" if tool_complexity == "complex" else "⚡"
                    self._write_log(f"   Complexidade: {complexity_icon} {tool_complexity.upper()}\n")
                    self._write_log(f"   Argumentos:\n")
                    for arg_name, arg_value in tool_args.items():
                        arg_str = str(arg_value)
                        if len(arg_str) > 100:
                            arg_str = arg_str[:100] + "..."
                        self._write_log(f"      {arg_name}: {arg_str}\n")
                    
                    if self.verbose:
                        args_str = json.dumps(tool_args, indent=2)
                        self.console.print(
                            f"\n[yellow]🔧 Executando:[/yellow] [cyan]{tool_name}[/cyan]\n"
                            f"[dim]{args_str}[/dim]"
                        )
                    
                    # Executa a ferramenta
                    if tool_name in self.tools_registry:
                        tool_result = self.tools_registry[tool_name](**tool_args)
                    else:
                        tool_result = f"✗ Ferramenta '{tool_name}' não encontrada"
                    
                    # 🆕 Log resultado
                    result_preview = tool_result[:500] if len(tool_result) > 500 else tool_result
                    self._write_log(f"   Resultado: {result_preview}")
                    if len(tool_result) > 500:
                        self._write_log(f"... (truncado, total: {len(tool_result)} chars)")
                    self._write_log(f"\n\n")
                    
                    if self.verbose:
                        result_preview = tool_result[:200] + "..." if len(tool_result) > 200 else tool_result
                        self.console.print(f"[dim]→ Resultado: {result_preview}[/dim]")
                    
                    # Adiciona resultado ao histórico
                    messages.append({
                        "role": "tool",
                        "content": tool_result,
                        "tool_call_id": tool_call.id
                    })
                
                # 🆕 Seleciona modelo para próxima iteração baseado nas tools chamadas
                if message.tool_calls:
                    current_model = self._select_model_for_tools(message.tool_calls)
            
            # Máximo de iterações atingido
            # 🆕 Log limite atingido
            self._write_log(f"\n⚠️ LIMITE DE ITERAÇÕES ATINGIDO\n")
            self._write_log(f"   Iterações: {iteration}/{self.max_iterations}\n")
            self._write_log(f"   Tool calls executados: {total_tool_calls}\n")
            self._write_log(f"   Status: INCOMPLETO\n\n")
            
            if self.verbose:
                self.console.print(
                    f"\n[yellow]⚠️  Limite de {self.max_iterations} iterações atingido[/yellow]"
                )
            
            # 🆕 Salva memória mesmo em caso de falha
            result = {
                "success": False,
                "response": "Tarefa não concluída - limite de iterações atingido",
                "final_response": "Tarefa não concluída - limite de iterações atingido",
                "iterations": iteration,
                "tool_calls": total_tool_calls,
                "messages": messages,
                "timestamp": datetime.now().isoformat(),
                # 🆕 Tokens usage
                "tokens": {
                    "prompt_tokens": total_prompt_tokens,
                    "completion_tokens": total_completion_tokens,
                    "total_tokens": total_tokens
                }
            }
            
            # Cria resumo da tarefa (mesmo falhada)
            summary = self._create_task_summary(task, messages, result)
            self.task_summaries.append(summary)
            
            # Salva mensagens completas (mantém apenas últimas 3)
            self.conversation_history.append(messages.copy())
            if len(self.conversation_history) > self.max_history_tasks:
                self.conversation_history.pop(0)
            
            # 🆕 Log sumário final (falha)
            self._write_log(f"\n{'='*80}\n")
            self._write_log(f"📊 SUMÁRIO DA TAREFA #{self.task_counter}\n")
            self._write_log(f"{'='*80}\n")
            self._write_log(f"Status: ⚠️ INCOMPLETA (limite atingido)\n")
            self._write_log(f"Iterações: {iteration}/{self.max_iterations}\n")
            self._write_log(f"Tool calls: {total_tool_calls}\n")
            self._write_log(f"Tokens (Request): {total_prompt_tokens:,}\n")
            self._write_log(f"Tokens (Response): {total_completion_tokens:,}\n")
            self._write_log(f"Tokens (Total): {total_tokens:,}\n")
            self._write_log(f"Tempo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._write_log(f"{'='*80}\n")
            
            # 🆕 Mostra tokens no console se verbose
            if self.verbose:
                self.console.print(f"\n[yellow]📊 Uso de Tokens:[/yellow]")
                self.console.print(f"[dim]  Request (input): {total_prompt_tokens:,}[/dim]")
                self.console.print(f"[dim]  Response (output): {total_completion_tokens:,}[/dim]")
                self.console.print(f"[dim]  Total: {total_tokens:,}[/dim]")
            
            return result
        
        except Exception as e:
            error_msg = f"Erro na execução: {e}"
            
            # 🆕 Log erro
            self._write_log(f"\n❌ ERRO DE EXECUÇÃO\n")
            self._write_log(f"{'-'*80}\n")
            self._write_log(f"Erro: {error_msg}\n")
            self._write_log(f"Tipo: {type(e).__name__}\n")
            import traceback
            self._write_log(f"Traceback:\n{traceback.format_exc()}\n")
            self._write_log(f"{'-'*80}\n\n")
            
            if self.verbose:
                self.console.print(f"[red]❌ {error_msg}[/red]")
            
            # 🆕 Salva memória mesmo em caso de exceção
            result = {
                "success": False,
                "response": error_msg,
                "final_response": error_msg,
                "iterations": iteration if 'iteration' in locals() else 0,
                "tool_calls": total_tool_calls if 'total_tool_calls' in locals() else 0,
                "error": str(e),
                "messages": messages if 'messages' in locals() else [],
                "timestamp": datetime.now().isoformat(),
                # 🆕 Tokens usage (pode ser parcial se erro ocorreu no meio)
                "tokens": {
                    "prompt_tokens": total_prompt_tokens if 'total_prompt_tokens' in locals() else 0,
                    "completion_tokens": total_completion_tokens if 'total_completion_tokens' in locals() else 0,
                    "total_tokens": total_tokens if 'total_tokens' in locals() else 0
                }
            }
            
            # Cria resumo da tarefa (mesmo com erro)
            if 'messages' in locals():
                summary = self._create_task_summary(task, messages, result)
                self.task_summaries.append(summary)
                
                # Salva mensagens completas (mantém apenas últimas 3)
                self.conversation_history.append(messages.copy())
                if len(self.conversation_history) > self.max_history_tasks:
                    self.conversation_history.pop(0)
            
            # 🆕 Log sumário final (erro)
            self._write_log(f"\n{'='*80}\n")
            self._write_log(f"📊 SUMÁRIO DA TAREFA #{self.task_counter}\n")
            self._write_log(f"{'='*80}\n")
            self._write_log(f"Status: ❌ ERRO\n")
            self._write_log(f"Iterações: {iteration if 'iteration' in locals() else 0}\n")
            self._write_log(f"Tool calls: {total_tool_calls if 'total_tool_calls' in locals() else 0}\n")
            self._write_log(f"Tokens (Request): {total_prompt_tokens if 'total_prompt_tokens' in locals() else 0:,}\n")
            self._write_log(f"Tokens (Response): {total_completion_tokens if 'total_completion_tokens' in locals() else 0:,}\n")
            self._write_log(f"Tokens (Total): {total_tokens if 'total_tokens' in locals() else 0:,}\n")
            self._write_log(f"Tempo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._write_log(f"{'='*80}\n")
            
            # 🆕 Mostra tokens no console se verbose
            if self.verbose and 'total_tokens' in locals() and total_tokens > 0:
                self.console.print(f"\n[red]📊 Uso de Tokens (até o erro):[/red]")
                self.console.print(f"[dim]  Request (input): {total_prompt_tokens:,}[/dim]")
                self.console.print(f"[dim]  Response (output): {total_completion_tokens:,}[/dim]")
                self.console.print(f"[dim]  Total: {total_tokens:,}[/dim]")
            
            return result
    
    def chat(self):
        """Modo de chat interativo"""
        self.console.print(Panel(
            "[cyan]🤖 Modern AI Agent - Chat Interativo[/cyan]\n"
            "[dim]Digite suas tarefas. Use 'sair' para encerrar.[/dim]",
            border_style="cyan",
            box=box.DOUBLE
        ))
        
        while True:
            task = Prompt.ask("\n[yellow]Você[/yellow]")
            
            if task.lower() in ['sair', 'exit', 'quit', 'q']:
                self.console.print("[cyan]👋 Até logo![/cyan]")
                break
            
            if not task.strip():
                continue
            
            self.execute_task(task)


def demo():
    """Demonstração do Modern AI Agent"""
    console = Console()
    
    console.print(Panel.fit(
        "[bold cyan]🚀 Modern AI Code Agent[/bold cyan]\n"
        "[dim]Arquitetura 2025 - OpenAI Function Calling[/dim]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    
    try:
        agent = ModernAIAgent(verbose=True)
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        console.print("\n[yellow]Configure OPENAI_API_KEY no arquivo .env[/yellow]")
        return
    
    while True:
        console.print("\n[bold cyan]═══ MENU ═══[/bold cyan]")
        console.print("[1] 💬 Chat Interativo")
        console.print("[2] 📝 Executar tarefa única")
        console.print("[3] 🧪 Exemplo: Listar arquivos Python")
        console.print("[4] 🧪 Exemplo: Analisar arquivo")
        console.print("[5] 🧪 Exemplo: Refatorar código")
        console.print("[6] 🧪 Exemplo: Criar novo arquivo")
        console.print("[7] 🐚 Exemplo: Executar comando shell")
        console.print("[8] 📜 Exemplo: Executar script shell")
        console.print("[9] 🔧 Exemplo: Git operations")
        console.print("[0] ❌ Sair")
        
        choice = Prompt.ask(
            "[yellow]Escolha[/yellow]",
            choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
            default="1"
        )
        
        if choice == "1":
            agent.chat()
        
        elif choice == "2":
            task = Prompt.ask("📝 Descreva a tarefa")
            agent.execute_task(task)
        
        elif choice == "3":
            agent.execute_task("Liste todos os arquivos Python (*.py) no workspace")
        
        elif choice == "4":
            filepath = Prompt.ask("📄 Arquivo", default="code_agent.py")
            agent.execute_task(
                f"Analise o arquivo {filepath} e me diga:\n"
                f"1. O que ele faz\n"
                f"2. Principais classes/funções\n"
                f"3. Possíveis melhorias"
            )
        
        elif choice == "5":
            filepath = Prompt.ask("📄 Arquivo para refatorar")
            agent.execute_task(
                f"Refatore o arquivo {filepath}:\n"
                f"1. Primeiro leia o arquivo\n"
                f"2. Identifique nomes de variáveis ruins\n"
                f"3. Sugira e aplique melhorias\n"
                f"4. Adicione comentários onde necessário"
            )
        
        elif choice == "6":
            filepath = Prompt.ask("📄 Nome do novo arquivo")
            description = Prompt.ask("✨ O que deve conter?")
            agent.execute_task(
                f"Crie um novo arquivo {filepath}:\n{description}\n\n"
                f"O código deve ser bem estruturado e documentado."
            )
        
        elif choice == "7":
            agent.execute_task(
                "Execute o comando 'ls -lah' para listar todos os arquivos do workspace "
                "incluindo ocultos, mostrando tamanhos legíveis"
            )
        
        elif choice == "8":
            agent.execute_task("""
Execute um script shell que:
1. Mostra informações do sistema (uname -a)
2. Mostra uso de disco (df -h)
3. Conta quantos arquivos Python existem
4. Mostra as 5 últimas linhas do README se existir
""")
        
        elif choice == "9":
            agent.execute_task("""
Execute comandos git para verificar o status do repositório:
1. Mostre o status atual (git status)
2. Mostre a branch atual (git branch)
3. Mostre os últimos 3 commits (git log -3 --oneline)
4. Mostre arquivos modificados mas não commitados
""")
        
        elif choice == "0":
            console.print("\n[cyan]👋 Até logo![/cyan]")
            break


if __name__ == "__main__":
    demo()

