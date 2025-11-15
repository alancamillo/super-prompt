#!/usr/bin/env python3
"""
Modern AI Code Agent - Arquitetura 2025
Implementação moderna usando OpenAI Function Calling nativo
Baseado em melhores práticas de arquitetura de agentes
"""

import os
import json
import subprocess
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

from .code_agent import CodeAgent
from .config import AgentConfig
from .tools import ToolManager
from .tool_decorator import TOOL_REGISTRY, TOOL_SCHEMAS, TOOL_COMPLEXITY

class ModernAIAgent:
    """
    Agente de IA moderno usando OpenAI Function Calling.
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Inicializa o Modern AI Agent.
        
        Args:
            config: Objeto de configuração Pydantic. Se não fornecido, usa valores padrão.
        """
        self.config = config or AgentConfig()
        self.console = Console()
        
        self.workspace = Path(self.config.workspace).resolve()
        self.max_iterations = self.config.max_iterations
        self.verbose = self.config.verbose
        self.use_multi_model = self.config.use_multi_model
        
        self._setup_logging()
        self._validate_models()
        
        # Carrega API key
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY não encontrada no .env")
        
        self.client = OpenAI(api_key=api_key)
        self.code_agent = CodeAgent(str(self.workspace))
        
        # Instancia o ToolManager e registra as ferramentas
        self.tool_manager = ToolManager(self.workspace, self.code_agent)
        self._register_tools()
        
        # Memória e estado
        self.max_history_tasks = self.config.max_history_tasks
        self.conversation_history: List[List[Dict[str, Any]]] = []
        self.task_summaries: List[Dict[str, Any]] = []
        self.task_counter: int = 0
        
        if self.verbose:
            self._display_initialization_message()

    def _setup_logging(self):
        """Configura o sistema de logging."""
        self.log_file = self.config.log_file
        self.log_handle = None
        if self.log_file:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_handle = open(log_path, 'a', encoding='utf-8')
            self._write_log(f"\n{'='*80}\n")
            self._write_log(f"🚀 NOVA SESSÃO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._write_log(f"{'='*80}\n")

    def _validate_models(self):
        """Valida os modelos OpenAI configurados."""
        valid_models = ['gpt-5', 'gpt-5-mini', 'gpt-5-nano', 'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo']
        
        if self.config.model:
            if self.config.model not in valid_models:
                self.console.print(f"[yellow]⚠️ Aviso: Modelo '{self.config.model}' pode não ser válido.[/yellow]")
            self.default_model = self.config.model
            self.simple_model = self.config.model
            self.complex_model = self.config.model
            self.use_multi_model = False
        else:
            if self.config.simple_model not in valid_models:
                self.console.print(f"[yellow]⚠️ Aviso: Modelo simples '{self.config.simple_model}' pode não ser válido.[/yellow]")
            if self.config.complex_model not in valid_models:
                self.console.print(f"[yellow]⚠️ Aviso: Modelo complexo '{self.config.complex_model}' pode não ser válido.[/yellow]")
            self.default_model = self.config.simple_model
            self.simple_model = self.config.simple_model
            self.complex_model = self.config.complex_model

    def _register_tools(self):
        """Registra as ferramentas a partir do ToolManager e dos decoradores."""
        self.tools_registry = {name: getattr(self.tool_manager, name) for name in TOOL_REGISTRY}
        self.tools_schema = TOOL_SCHEMAS
        self.tool_complexity = TOOL_COMPLEXITY

    def _display_initialization_message(self):
        """Mostra a mensagem de inicialização com base na configuração."""
        if self.use_multi_model:
            self.console.print(
                f"[green]✓ Modern AI Agent inicializado[/green]\n"
                f"[dim]  Modo: Multi-Model (seleção automática)[/dim]\n"
                f"[dim]  ⚡ Simple: {self.simple_model}[/dim]\n"
                f"[dim]  🧠 Complex: {self.complex_model}[/dim]\n"
                f"[dim]  Workspace: {self.workspace}[/dim]\n"
                f"[dim]  Tools: {len(self.tools_registry)} ({sum(1 for c in self.tool_complexity.values() if c == 'complex')} complexas)[/dim]"
            )
        else:
            self.console.print(
                f"[green]✓ Modern AI Agent inicializado[/green]\n"
                f"[dim]  Modelo: {self.default_model}[/dim]\n"
                f"[dim]  Workspace: {self.workspace}[/dim]\n"
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
        """Escreve mensagem no arquivo de log."""
        if self.log_handle:
            try:
                self.log_handle.write(message)
                self.log_handle.flush()
            except Exception as e:
                if self.verbose:
                    self.console.print(f"[yellow]⚠️ Erro ao escrever log: {e}[/yellow]")
    
    def _select_model_for_tools(self, tool_calls: List[Any]) -> str:
        """Seleciona o modelo apropriado baseado nas ferramentas sendo chamadas."""
        if not self.use_multi_model:
            return self.default_model
        
        has_complex_tool = any(
            self.tool_complexity.get(getattr(tool_call.function, 'name', '')) == "complex"
            for tool_call in tool_calls
        )
        
        model_to_use = self.complex_model if has_complex_tool else self.simple_model
        
        if self.verbose and has_complex_tool:
            self.console.print(f"[dim]🧠 Usando modelo poderoso ({model_to_use}) para ferramentas complexas[/dim]")
        
        return model_to_use

    def execute_task(
        self,
        task: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executa uma tarefa usando o padrão ReAct.
        """
        self.task_counter += 1
        self._write_log(f"\n{'─'*80}\n📋 TAREFA #{self.task_counter}: {task}\n{'─'*80}\n")

        if self.verbose:
            self.console.print(Panel(f"[cyan]🤖 Tarefa #{self.task_counter}:[/cyan]\n{task}", border_style="cyan"))

        history_context = self._build_context_from_history()
        
        if not system_prompt:
            system_prompt = f"Você é um assistente de codificação de IA. Seu objetivo é completar a tarefa dada pelo usuário. Você está trabalhando no diretório: {self.workspace}"
        
        if history_context:
            system_prompt += "\n\n" + history_context

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": task}]
        
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            if self.verbose:
                self.console.print(f"\n[dim]═══ Iteração {iteration}/{self.max_iterations} ═══[/dim]")

            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                tools=self.tools_schema,
                tool_choice="auto"
            )
            message = response.choices[0].message
            messages.append(message)

            if not message.tool_calls:
                if self.verbose:
                    self.console.print(Panel(f"[green]✓ Tarefa concluída![/green]\n\n{message.content}", border_style="green"))
                return {"success": True, "response": message.content}

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                if self.verbose:
                    self.console.print(f"\n[yellow]🔧 Executando:[/yellow] [cyan]{tool_name}[/cyan]")
                
                if tool_name in self.tools_registry:
                    tool_result = self.tools_registry[tool_name](**tool_args)
                else:
                    tool_result = f"✗ Ferramenta '{tool_name}' não encontrada"
                
                if self.verbose:
                    self.console.print(f"[dim]→ Resultado: {tool_result[:200]}...[/dim]")
                
                messages.append({"role": "tool", "content": tool_result, "tool_call_id": tool_call.id})

        return {"success": False, "response": "Limite de iterações atingido."}

    def _create_task_summary(self, task: str, messages: List[Dict[str, Any]], result: Dict[str, Any]) -> Dict[str, Any]:
        # Dummy implementation, needs to be filled out
        return {"task": task, "status": "completed"}

    def _build_context_from_history(self) -> str:
        # Dummy implementation, needs to be filled out
        return ""

    def chat(self):
        """Modo de chat interativo"""
        self.console.print(Panel("[cyan]🤖 Modern AI Agent - Chat Interativo[/cyan]", border_style="cyan"))
        while True:
            task = Prompt.ask("\n[yellow]Você[/yellow]")
            if task.lower() in ['sair', 'exit', 'quit', 'q']:
                break
            if task.strip():
                self.execute_task(task)

def demo():
    """Demonstração do Modern AI Agent"""
    try:
        agent = ModernAIAgent()
        agent.chat()
    except ValueError as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    demo()

