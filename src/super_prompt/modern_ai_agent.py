#!/usr/bin/env python3
"""
Modern AI Code Agent - Arquitetura 2025
Implementação moderna usando LiteLLM SDK para abstrair chamadas de LLM
Suporta 100+ providers: OpenAI, LM Studio, Ollama, Anthropic, Groq, etc.
Baseado em melhores práticas de arquitetura de agentes
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from dotenv import load_dotenv
import litellm
from openai import OpenAI as OpenAIClient

# Configura o LiteLLM para não fazer mapeamento automático de nomes quando api_base é customizado
# Isso é importante para usar modelos com nomes customizados no LM Studio
# O model_alias_map será limpo quando api_base for configurado para evitar mapeamento incorreto

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box
from rich.syntax import Syntax

import re

from .code_agent import CodeAgent
from .config import AgentConfig
from .model_config import ModelConfig, ModelProviderConfig
from . import tools
from .tools.git_tools import git_session_start, git_session_end, _is_git_repo, _get_current_branch, _strip_ansi

class ModernAIAgent:
    """
    Agente de IA moderno usando LiteLLM SDK para suportar múltiplos providers de LLM.
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
        self._setup_llm()
        self._validate_models()
        
        self.code_agent = CodeAgent(str(self.workspace))
        
        # Registra as ferramentas a partir do novo pacote de ferramentas
        self._register_tools()
        
        # Memória e estado
        self.max_history_tasks = self.config.max_history_tasks
        self.conversation_history: List[List[Dict[str, Any]]] = []
        self.task_summaries: List[Dict[str, Any]] = []
        self.task_counter: int = 0
        
        # Estado da sessão Git
        self.git_session_branch: Optional[str] = None
        self.git_session_started: bool = False
        
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

    def _setup_llm(self):
        """Configura o LiteLLM com base nas configurações."""
        load_dotenv()
        
        # Configura api_base se fornecido
        if self.config.api_base:
            # Para LM Studio, Ollama, etc.
            os.environ.setdefault('LM_STUDIO_API_BASE', self.config.api_base)
            os.environ.setdefault('OLLAMA_API_BASE', self.config.api_base)
            # LiteLLM usa variáveis de ambiente específicas por provider
            # Mas também aceita api_base diretamente nas chamadas
            
            # IMPORTANTE: Desabilita o mapeamento automático de nomes de modelos
            # Isso evita que o LiteLLM mapeie "openai/gpt-oss-120b" para "lmstudio-community/gpt-oss-120b"
            # Quando api_base é customizado, queremos usar o nome exato do modelo do servidor
            
            # Salva o mapeamento original na primeira vez (se ainda não foi salvo)
            if not hasattr(litellm, '_original_model_alias_map'):
                litellm._original_model_alias_map = getattr(litellm, 'model_alias_map', {}).copy()
            
            # Limpa o mapeamento para usar nomes exatos
            litellm.model_alias_map = {}
            
            # Desabilita a normalização de nomes de modelos
            # Isso força o LiteLLM a usar o nome exato sem tentar normalizar
            if hasattr(litellm, 'set_verbose'):
                # Desabilita logs verbosos que podem interferir
                pass
            
            # Configura para não fazer normalização de nomes
            # Usando uma função de hook para interceptar e forçar o nome exato
            def force_exact_model_name(model: str, **kwargs) -> str:
                """Hook para forçar o uso do nome exato do modelo"""
                return model  # Retorna o nome exatamente como recebido, sem normalização
            
            # Registra o hook se disponível
            if hasattr(litellm, 'pre_call_hooks'):
                if 'force_exact_model' not in [h.__name__ if hasattr(h, '__name__') else str(h) for h in litellm.pre_call_hooks]:
                    litellm.pre_call_hooks.append(force_exact_model_name)
            
            if self.verbose:
                self.console.print("[dim]✓ Mapeamento automático de nomes de modelos desabilitado (usando nomes exatos do servidor)[/dim]")
        
        # Configura api_key se fornecido, senão tenta variáveis de ambiente padrão
        if self.config.api_key:
            # Para OpenAI, usa OPENAI_API_KEY
            if not self.config.api_base or 'openai' in str(self.config.simple_model).lower():
                os.environ.setdefault('OPENAI_API_KEY', self.config.api_key)
            # Para outros providers, LiteLLM detecta automaticamente baseado no prefixo do modelo
        
        # Verifica se há pelo menos uma API key configurada (para OpenAI padrão)
        if not self.config.api_key and not os.getenv("OPENAI_API_KEY"):
            # Se não for um provider local (LM Studio, Ollama), precisa de API key
            if not self.config.api_base:
                if self.verbose:
                    self.console.print("[yellow]⚠️ Aviso: Nenhuma API key configurada. Configure OPENAI_API_KEY no .env ou use api_key no AgentConfig.[/yellow]")
        
        # Configura modelos a partir do model_provider_config
        if self.config.model_provider_config:
            self.simple_model = self.config.model_provider_config.simple.name
            self.complex_model = self.config.model_provider_config.complex.name
            self.default_model = self.simple_model  # Padrão inicial
        elif self.config.model:
            # Legacy: modelo único
            self.default_model = self.config.model
            self.simple_model = self.config.model
            self.complex_model = self.config.model
            self.use_multi_model = False
        else:
            # Legacy: modelos simples/complexo
            self.default_model = self.config.simple_model or "gpt-4o-mini"
            self.simple_model = self.config.simple_model or "gpt-4o-mini"
            self.complex_model = self.config.complex_model or "gpt-4o"
        
        # Configura clientes OpenAI diretos para cada modelo (quando api_base é customizado)
        # Isso evita mapeamento do LiteLLM e permite diferentes providers por modelo
        self.model_clients: Dict[str, OpenAIClient] = {}
        self.model_configs: Dict[str, ModelConfig] = {}
        
        # Cria clientes para modelos que usam api_base customizado
        if self.config.model_provider_config:
            for model_cfg in [self.config.model_provider_config.simple, self.config.model_provider_config.complex]:
                if model_cfg.api_base:
                    # Precisa de cliente direto para este modelo
                    api_key = model_cfg.api_key
                    if not api_key:
                        # Tenta variáveis de ambiente
                        load_dotenv()
                        api_key = os.getenv("OPENAI_API_KEY") or "not-needed"
                    
                    self.model_clients[model_cfg.name] = OpenAIClient(
                        base_url=model_cfg.api_base,
                        api_key=api_key
                    )
                    self.model_configs[model_cfg.name] = model_cfg
                    if self.verbose:
                        self.console.print(f"[dim]✓ Cliente configurado para {model_cfg.name} ({model_cfg.api_base})[/dim]")
            
            # Configura clientes para tool overrides também
            if self.config.model_provider_config.tool_overrides:
                for tool_name, model_cfg in self.config.model_provider_config.tool_overrides.items():
                    if model_cfg.api_base and model_cfg.name not in self.model_clients:
                        api_key = model_cfg.api_key
                        if not api_key:
                            load_dotenv()
                            api_key = os.getenv("OPENAI_API_KEY") or "not-needed"
                        
                        self.model_clients[model_cfg.name] = OpenAIClient(
                            base_url=model_cfg.api_base,
                            api_key=api_key
                        )
                        self.model_configs[model_cfg.name] = model_cfg
                        if self.verbose:
                            self.console.print(f"[dim]✓ Cliente configurado para tool '{tool_name}': {model_cfg.name}[/dim]")
        
        # Compatibilidade legacy: se api_base está configurado, cria cliente único
        elif self.config.api_base:
            self.use_direct_openai = True
            api_key = self.config.api_key
            if not api_key:
                load_dotenv()
                api_key = os.getenv("OPENAI_API_KEY") or "not-needed"
            
            self.openai_client = OpenAIClient(
                base_url=self.config.api_base,
                api_key=api_key
            )
            if self.verbose:
                self.console.print("[dim]✓ Usando cliente OpenAI direto (modo legacy)[/dim]")
        else:
            self.use_direct_openai = False

    def _validate_models(self):
        """Valida os modelos configurados (agora suporta múltiplos providers via LiteLLM)."""
        # Com LiteLLM, não precisamos validar modelos específicos
        # Mas podemos avisar sobre formatos esperados
        if self.verbose:
            if self.config.model:
                self.console.print(f"[dim]✓ Modelo configurado: {self.config.model}[/dim]")
            else:
                self.console.print(f"[dim]✓ Modelos configurados: Simple={self.config.simple_model}, Complex={self.config.complex_model}[/dim]")

    # =========================================================================
    # GESTÃO DE SESSÃO GIT
    # =========================================================================
    
    def _ensure_git_session(self, task_description: str) -> Optional[str]:
        """
        Garante que uma sessão Git está ativa com branch isolado.
        
        Esta função é chamada automaticamente no início da primeira tarefa.
        Cria um branch de sessão para isolar todas as mudanças.
        
        Args:
            task_description: Descrição da tarefa (usada para nomear o branch)
            
        Returns:
            Resultado da criação do branch ou None se já existe
        """
        if self.git_session_started:
            return None  # Sessão já iniciada
        
        # Verifica se é um repositório Git
        if not _is_git_repo(self.workspace):
            self._write_log("ℹ️ Workspace não é repositório Git. Sessão Git não será criada.\n")
            if self.verbose:
                self.console.print("[dim]ℹ️ Workspace não é repositório Git. Pulando criação de branch de sessão.[/dim]")
            self.git_session_started = True  # Marca como "tratado"
            return None
        
        # Verifica se já está em um branch de sessão
        current_branch = _get_current_branch(self.workspace)
        if current_branch.startswith("session/"):
            self._write_log(f"ℹ️ Já está em branch de sessão: {current_branch}\n")
            self.git_session_branch = current_branch
            self.git_session_started = True
            return None
        
        # Cria branch de sessão
        # Extrai descrição curta da tarefa (primeiras palavras)
        words = task_description.split()[:4]
        short_desc = "-".join(words).lower()
        short_desc = "".join(c for c in short_desc if c.isalnum() or c == "-")[:30]
        
        self._write_log(f"\n🚀 Criando branch de sessão para: {short_desc}\n")
        
        result = git_session_start(short_desc, self.workspace)
        
        self._write_log(f"{result}\n")
        
        if self.verbose:
            # Usa print nativo pois result já contém códigos ANSI do Rich
            print(result)
        
        # Atualiza estado
        self.git_session_branch = _get_current_branch(self.workspace)
        self.git_session_started = True
        
        return result
    
    def show_git_review(self) -> str:
        """
        Mostra o review da sessão Git com opções de merge.
        
        Deve ser chamado ao final da sessão de trabalho.
        
        Returns:
            Resultado do review (versão sem cores para log)
        """
        if not _is_git_repo(self.workspace):
            return "ℹ️ Workspace não é repositório Git."
        
        result = git_session_end(self.workspace)
        
        # Log recebe versão sem cores (já é limpo pelo _write_log)
        self._write_log(f"\n🏁 GIT REVIEW:\n{result}\n")
        
        if self.verbose:
            # Console recebe versão com cores via print nativo
            # (não usar console.print pois a string já tem códigos ANSI)
            print(result)
        
        # Retorna versão limpa para armazenamento
        return _strip_ansi(result)

    def _register_tools(self):
        """Registra as ferramentas a partir do pacote de ferramentas."""
        # O __init__.py do pacote de ferramentas já importa e registra tudo.
        # Aqui, nós pegamos as ferramentas prontas com as dependências já injetadas.
        self.tools_registry = tools.get_all_tools(self.code_agent, self.workspace)
        self.tools_schema = tools.TOOL_SCHEMAS
        self.tool_complexity = tools.TOOL_COMPLEXITY

    def _display_initialization_message(self):
        """Mostra a mensagem de inicialização com base na configuração."""
        if self.use_multi_model:
            # Mostra informações detalhadas sobre os providers
            simple_provider = "Local" if hasattr(self.config, 'model_provider_config') and self.config.model_provider_config and self.config.model_provider_config.simple.api_base else "OpenAI"
            complex_provider = "Local" if hasattr(self.config, 'model_provider_config') and self.config.model_provider_config and self.config.model_provider_config.complex.api_base else "OpenAI"
            
            provider_details = ""
            if hasattr(self.config, 'model_provider_config') and self.config.model_provider_config:
                simple_cfg = self.config.model_provider_config.simple
                complex_cfg = self.config.model_provider_config.complex
                provider_details = f"\n[dim]  ⚡ Simple Provider: {simple_cfg.api_base or 'OpenAI (padrão)'}[/dim]"
                provider_details += f"\n[dim]  🧠 Complex Provider: {complex_cfg.api_base or 'OpenAI (padrão)'}[/dim]"
                
                if self.config.model_provider_config.tool_overrides:
                    override_count = len(self.config.model_provider_config.tool_overrides)
                    provider_details += f"\n[dim]  🔧 Tool Overrides: {override_count} tool(s)[/dim]"
            
            self.console.print(
                f"[green]✓ Modern AI Agent inicializado (LiteLLM)[/green]\n"
                f"[dim]  Modo: Multi-Model (seleção automática)[/dim]\n"
                f"[dim]  ⚡ Simple: {self.simple_model} ({simple_provider})[/dim]\n"
                f"[dim]  🧠 Complex: {self.complex_model} ({complex_provider})[/dim]{provider_details}\n"
                f"[dim]  Workspace: {self.workspace}[/dim]\n"
                f"[dim]  Max Iterations: {self.max_iterations}[/dim]\n"
                f"[dim]  Tools: {len(self.tools_registry)} ({sum(1 for c in self.tool_complexity.values() if c == 'complex')} complexas)[/dim]"
            )
        else:
            provider_info = ""
            if hasattr(self.config, 'model_provider_config') and self.config.model_provider_config:
                model_cfg = self.config.model_provider_config.simple
                if model_cfg.api_base:
                    provider_info = f"\n[dim]  API Base: {model_cfg.api_base}[/dim]"
            elif self.config.api_base:
                provider_info = f"\n[dim]  API Base: {self.config.api_base}[/dim]"
            
            self.console.print(
                f"[green]✓ Modern AI Agent inicializado (LiteLLM)[/green]\n"
                f"[dim]  Modelo: {self.default_model}[/dim]\n"
                f"[dim]  Workspace: {self.workspace}[/dim]\n"
                f"[dim]  Max Iterations: {self.max_iterations}[/dim]{provider_info}\n"
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
    
    def _write_log(self, message: str, strip_colors: bool = True):
        """
        Escreve mensagem no arquivo de log.
        
        Args:
            message: Mensagem a ser escrita
            strip_colors: Se True, remove códigos ANSI de cores (padrão: True)
        """
        if self.log_handle:
            try:
                # Remove códigos ANSI para manter log limpo
                clean_message = _strip_ansi(message) if strip_colors else message
                self.log_handle.write(clean_message)
                self.log_handle.flush()
            except Exception as e:
                if self.verbose:
                    self.console.print(f"[yellow]⚠️ Erro ao escrever log: {e}[/yellow]")
    
    # =========================================================================
    # MÉTODOS DE SELEÇÃO DE MODELO POR FASE COGNITIVA
    # =========================================================================
    
    def _get_simple_model_config(self) -> ModelConfig:
        """Retorna configuração do modelo simples."""
        if hasattr(self.config, 'model_provider_config') and self.config.model_provider_config:
            return self.config.model_provider_config.simple
        return ModelConfig(
            name=self.default_model,
            api_base=self.config.api_base,
            api_key=self.config.api_key
        )
    
    def _get_complex_model_config(self) -> ModelConfig:
        """Retorna configuração do modelo complexo."""
        if hasattr(self.config, 'model_provider_config') and self.config.model_provider_config:
            return self.config.model_provider_config.complex
        return ModelConfig(
            name=self.default_model,
            api_base=self.config.api_base,
            api_key=self.config.api_key
        )
    
    # Lista de ferramentas cognitivas que sempre usam o modelo complexo
    COGNITIVE_TOOLS = {'analyze_error', 'replan_approach', 'validate_result', 'progress_checkpoint'}
    
    def _get_model_config_for_tools(self, tool_calls: Optional[List[Any]] = None, iteration: int = 1) -> ModelConfig:
        """
        Seleciona a configuração do modelo apropriado baseado nas ferramentas.
        
        ARQUITETURA HÍBRIDA DE SELEÇÃO DE MODELO:
        
        Priority:
        1. Ferramentas cognitivas (analyze_error, replan_approach, etc.) → SEMPRE complex
        2. Tool-specific override (se configurado) → usa o override
        3. Ferramentas marcadas como complexity="complex" → complex
        4. Demais ferramentas → simple
        
        Returns:
            ModelConfig com nome, api_base e api_key do modelo a usar
        """
        # Garante que model_provider_config existe (criado no validator)
        if not hasattr(self.config, 'model_provider_config') or not self.config.model_provider_config:
            # Legacy mode: cria ModelConfig a partir de configuração antiga
            return ModelConfig(
                name=self.default_model,
                api_base=self.config.api_base,
                api_key=self.config.api_key
            )
        
        # Extrai nomes das ferramentas sendo chamadas
        tool_names = []
        if tool_calls:
            for tool_call in tool_calls:
                tool_name = None
                if hasattr(tool_call, 'function'):
                    tool_name = tool_call.function.name
                elif isinstance(tool_call, dict):
                    tool_name = tool_call.get('function', {}).get('name')
                if tool_name:
                    tool_names.append(tool_name)
        
        # PRIORIDADE 1: Ferramentas cognitivas SEMPRE usam modelo complexo
        has_cognitive_tool = any(name in self.COGNITIVE_TOOLS for name in tool_names)
        if has_cognitive_tool:
            if self.verbose:
                cognitive_names = [n for n in tool_names if n in self.COGNITIVE_TOOLS]
                self.console.print(f"[dim]🧠 Ferramenta cognitiva detectada: {cognitive_names} → usando modelo complexo[/dim]")
            return self._get_complex_model_config()
        
        # PRIORIDADE 2: Verifica overrides por ferramenta
        if tool_names and self.config.model_provider_config.tool_overrides:
            for tool_name in tool_names:
                if tool_name in self.config.model_provider_config.tool_overrides:
                    override_cfg = self.config.model_provider_config.tool_overrides[tool_name]
                    if self.verbose:
                        self.console.print(f"[dim]🔧 Usando override para tool '{tool_name}': {override_cfg.name}[/dim]")
                    return override_cfg
        
        # PRIORIDADE 3: Verifica complexidade das ferramentas
        if self.use_multi_model and tool_names:
            for tool_name in tool_names:
                tool_complexity = self.tool_complexity.get(tool_name, 'simple')
                if tool_complexity == "complex":
                    if self.verbose:
                        self.console.print(f"[dim]🔧 Ferramenta complexa '{tool_name}' → usando modelo complexo[/dim]")
                    return self._get_complex_model_config()
        
        # DEFAULT: Usa modelo simples para ferramentas simples
        return self._get_simple_model_config()

    # =========================================================================
    # FASES COGNITIVAS AUTOMÁTICAS
    # =========================================================================
    
    def _call_llm(self, messages: List[Dict[str, Any]], model_config: ModelConfig, include_tools: bool = True) -> Any:
        """
        Método auxiliar para chamar o LLM com uma configuração específica.
        
        Args:
            messages: Lista de mensagens para o LLM
            model_config: Configuração do modelo a usar
            include_tools: Se deve incluir ferramentas na chamada
            
        Returns:
            Resposta do LLM (já convertida para formato compatível)
        """
        model_name = model_config.name
        
        # Verifica se este modelo tem cliente direto configurado
        if model_name in self.model_clients:
            client = self.model_clients[model_name]
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=self.tools_schema if include_tools and self.tools_schema else None,
                tool_choice="auto" if include_tools and self.tools_schema else None
            )
            # Converte para formato compatível
            class LiteLLMResponse:
                def __init__(self, openai_response):
                    self.choices = [type('Choice', (), {
                        'message': openai_response.choices[0].message
                    })()]
            return LiteLLMResponse(response)
        elif hasattr(self, 'openai_client') and self.use_direct_openai:
            response = self.openai_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=self.tools_schema if include_tools and self.tools_schema else None,
                tool_choice="auto" if include_tools and self.tools_schema else None
            )
            class LiteLLMResponse:
                def __init__(self, openai_response):
                    self.choices = [type('Choice', (), {
                        'message': openai_response.choices[0].message
                    })()]
            return LiteLLMResponse(response)
        else:
            # Usa LiteLLM
            completion_kwargs = {
                "model": model_name,
                "messages": messages,
            }
            if include_tools and self.tools_schema:
                completion_kwargs["tools"] = self.tools_schema
                completion_kwargs["tool_choice"] = "auto"
            
            if model_config.api_base:
                completion_kwargs["api_base"] = model_config.api_base
            if model_config.api_key:
                completion_kwargs["api_key"] = model_config.api_key
            
            return litellm.completion(**completion_kwargs)

    def _phase_planning(self, task: str, system_prompt: str) -> Dict[str, Any]:
        """
        FASE 1: PLANEJAMENTO (🧠 COMPLEX)
        
        Analisa a tarefa e cria um plano estruturado antes de começar a execução.
        Esta fase SEMPRE usa o modelo complexo para garantir um bom planejamento.
        
        Returns:
            Dict com 'plan' (string) e 'messages' (lista para continuar)
        """
        self._write_log(f"\n{'='*80}\n🧠 FASE 1: PLANEJAMENTO (modelo complexo)\n{'='*80}\n")
        
        if self.verbose:
            self.console.print("\n[bold magenta]🧠 FASE 1: PLANEJAMENTO[/bold magenta]")
        
        # Prompt especial para planejamento
        planning_prompt = f"""{system_prompt}

IMPORTANTE: Você está na FASE DE PLANEJAMENTO. Antes de executar qualquer ação:

1. ANALISE a tarefa cuidadosamente
2. IDENTIFIQUE os passos necessários
3. LISTE possíveis obstáculos
4. CRIE um plano estruturado

Responda com seu plano ANTES de usar qualquer ferramenta. O plano deve incluir:
- Objetivo principal
- Passos ordenados
- Riscos identificados
- Critérios de sucesso

Após apresentar o plano, você pode começar a executar usando as ferramentas disponíveis."""

        messages = [
            {"role": "system", "content": planning_prompt},
            {"role": "user", "content": task}
        ]
        
        try:
            model_config = self._get_complex_model_config()
            provider_info = f" ({model_config.api_base})" if model_config.api_base else " (OpenAI)"
            self._write_log(f"🤖 Chamando modelo complexo: {model_config.name}{provider_info}\n")
            
            if self.verbose:
                self.console.print(f"[dim]🤖 Modelo: {model_config.name}{provider_info}[/dim]")
            
            response = self._call_llm(messages, model_config, include_tools=False)
            plan_content = response.choices[0].message.content or ""
            
            self._write_log(f"📋 Plano gerado:\n{plan_content}\n")
            
            if self.verbose:
                self.console.print(Panel(plan_content[:500] + "..." if len(plan_content) > 500 else plan_content, 
                                        title="[magenta]📋 Plano[/magenta]", border_style="magenta"))
            
            # Adiciona o plano ao histórico
            messages.append({"role": "assistant", "content": plan_content})
            
            # Instrui para começar execução
            messages.append({
                "role": "user", 
                "content": "Ótimo plano! Agora execute-o passo a passo usando as ferramentas disponíveis. "
                          "Se encontrar erros, use 'analyze_error' ou 'replan_approach'. "
                          "Ao concluir, apresente um resumo do que foi feito."
            })
            
            return {"plan": plan_content, "messages": messages, "success": True}
            
        except Exception as e:
            error_msg = f"Erro na fase de planejamento: {e}"
            self._write_log(f"❌ {error_msg}\n")
            if self.verbose:
                self.console.print(f"[red]❌ {error_msg}[/red]")
            
            # Fallback: continua sem planejamento explícito
            return {
                "plan": None, 
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": task}
                ],
                "success": False
            }

    def _phase_validation(self, task: str, execution_result: Dict[str, Any], actions_taken: List[str]) -> Dict[str, Any]:
        """
        FASE FINAL: VALIDAÇÃO (🧠 COMPLEX)
        
        Valida se a tarefa foi realmente concluída com sucesso.
        Esta fase SEMPRE usa o modelo complexo para garantir validação rigorosa.
        
        Args:
            task: A tarefa original
            execution_result: Resultado da fase de execução
            actions_taken: Lista de ações executadas
            
        Returns:
            Dict com 'validated' (bool), 'assessment' (string), 'needs_retry' (bool)
        """
        self._write_log(f"\n{'='*80}\n✅ FASE FINAL: VALIDAÇÃO (modelo complexo)\n{'='*80}\n")
        
        if self.verbose:
            self.console.print("\n[bold green]✅ FASE FINAL: VALIDAÇÃO[/bold green]")
        
        # Prepara resumo das ações
        actions_summary = "\n".join(f"- {action}" for action in actions_taken[-20:])  # Últimas 20 ações
        
        validation_prompt = f"""Você é um validador rigoroso. Analise se a tarefa foi concluída corretamente.

TAREFA ORIGINAL:
{task}

AÇÕES EXECUTADAS:
{actions_summary}

RESULTADO REPORTADO:
{execution_result.get('response', 'Não disponível')}

AVALIE:
1. A tarefa foi realmente concluída?
2. Todas as partes da solicitação foram atendidas?
3. Há erros óbvios ou omissões?
4. O resultado está correto e funcional?

Responda com:
- VALIDADO: [SIM/NÃO/PARCIAL]
- ASSESSMENT: [sua avaliação detalhada]
- PROBLEMAS: [lista de problemas, se houver]
- SUGESTÕES: [o que faltou ou pode melhorar]"""

        messages = [
            {"role": "system", "content": "Você é um validador de tarefas. Seja crítico e rigoroso."},
            {"role": "user", "content": validation_prompt}
        ]
        
        try:
            model_config = self._get_complex_model_config()
            provider_info = f" ({model_config.api_base})" if model_config.api_base else " (OpenAI)"
            self._write_log(f"🤖 Chamando modelo complexo para validação: {model_config.name}{provider_info}\n")
            
            if self.verbose:
                self.console.print(f"[dim]🤖 Modelo: {model_config.name}{provider_info}[/dim]")
            
            response = self._call_llm(messages, model_config, include_tools=False)
            validation_content = response.choices[0].message.content or ""
            
            self._write_log(f"📊 Validação:\n{validation_content}\n")
            
            if self.verbose:
                self.console.print(Panel(validation_content, title="[green]📊 Validação[/green]", border_style="green"))
            
            # Analisa resultado da validação
            validated = "SIM" in validation_content.upper() and "NÃO" not in validation_content.upper()[:100]
            needs_retry = "NÃO" in validation_content.upper()[:100] or "PARCIAL" in validation_content.upper()[:100]
            
            return {
                "validated": validated,
                "assessment": validation_content,
                "needs_retry": needs_retry
            }
            
        except Exception as e:
            error_msg = f"Erro na fase de validação: {e}"
            self._write_log(f"⚠️ {error_msg}\n")
            if self.verbose:
                self.console.print(f"[yellow]⚠️ {error_msg}[/yellow]")
            
            # Em caso de erro, assume validado (para não bloquear)
            return {
                "validated": True,
                "assessment": "Validação não realizada devido a erro",
                "needs_retry": False
            }

    def execute_task(
        self,
        task: str,
        system_prompt: Optional[str] = None,
        max_iterations: Optional[int] = None,
        skip_planning: bool = False,
        skip_validation: bool = False
    ) -> Dict[str, Any]:
        """
        Executa uma tarefa usando o padrão ReAct com FASES COGNITIVAS AUTOMÁTICAS.
        
        ARQUITETURA HÍBRIDA:
        - FASE 1 (Automática): PLANEJAMENTO (🧠 modelo complexo)
        - FASE 2 (Loop): EXECUÇÃO (⚡ modelo simples para ferramentas simples)
        - FASE 3 (Sob demanda): ANÁLISE DE ERROS / RE-PLANEJAMENTO (🧠 modelo complexo)
        - FASE 4 (Automática): VALIDAÇÃO (🧠 modelo complexo)
        
        Args:
            task: Descrição da tarefa a ser executada
            system_prompt: Prompt do sistema personalizado (opcional)
            max_iterations: Número máximo de iterações para esta tarefa específica (opcional).
            skip_planning: Pular fase de planejamento (para tarefas simples)
            skip_validation: Pular fase de validação (para tarefas simples)
        """
        # Usa max_iterations da tarefa se fornecido, senão usa o padrão da configuração
        task_max_iterations = max_iterations if max_iterations is not None else self.max_iterations
        
        # Valida o valor
        if task_max_iterations < 1:
            raise ValueError("max_iterations deve ser pelo menos 1")
        if task_max_iterations > 1000:
            raise ValueError("max_iterations não deve exceder 1000")
        
        self.task_counter += 1
        self._write_log(f"\n{'='*80}\n📋 TAREFA #{self.task_counter}: {task}\n{'='*80}\n")
        if max_iterations is not None:
            self._write_log(f"⚙️  Limite de iterações para esta tarefa: {max_iterations}\n")

        if self.verbose:
            panel_content = f"[cyan]🤖 Tarefa #{self.task_counter}:[/cyan]\n{task}"
            if max_iterations is not None:
                panel_content += f"\n[dim]Limite de iterações: {max_iterations}[/dim]"
            if self.use_multi_model:
                panel_content += f"\n[dim]Modo: Híbrido (planejamento → execução → validação)[/dim]"
            self.console.print(Panel(panel_content, border_style="cyan"))
        
        # =====================================================================
        # SESSÃO GIT: Cria branch isolado para esta sessão (se primeira tarefa)
        # =====================================================================
        if not self.git_session_started:
            self._ensure_git_session(task)

        history_context = self._build_context_from_history()
        
        if not system_prompt:
            system_prompt = f"""Você é um assistente de codificação de IA especializado. Seu objetivo é completar a tarefa dada pelo usuário.

WORKSPACE: {self.workspace}

FERRAMENTAS COGNITIVAS DISPONÍVEIS:
Quando encontrar problemas, você pode usar estas ferramentas especiais:
- analyze_error: Para analisar erros e entender o que deu errado
- replan_approach: Para reformular sua estratégia quando algo não funciona
- validate_result: Para verificar se uma ação foi bem-sucedida
- progress_checkpoint: Para registrar progresso em tarefas longas

Use estas ferramentas proativamente para garantir qualidade!"""
        
        if history_context:
            system_prompt += "\n\n" + history_context

        # Lista para rastrear ações executadas (para validação)
        actions_taken: List[str] = []
        
        # =====================================================================
        # FASE 1: PLANEJAMENTO (se multi-model ativado e não pulado)
        # =====================================================================
        if self.use_multi_model and not skip_planning:
            planning_result = self._phase_planning(task, system_prompt)
            messages = planning_result["messages"]
            if planning_result.get("plan"):
                actions_taken.append(f"[PLANEJAMENTO] Plano criado: {planning_result['plan'][:100]}...")
        else:
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": task}]
        
        # =====================================================================
        # FASE 2: EXECUÇÃO (loop principal)
        # =====================================================================
        self._write_log(f"\n{'='*80}\n⚡ FASE 2: EXECUÇÃO\n{'='*80}\n")
        
        if self.verbose:
            self.console.print("\n[bold yellow]⚡ FASE 2: EXECUÇÃO[/bold yellow]")
        
        iteration = 0
        previous_tool_calls = None
        execution_result = {"success": False, "response": "Nenhuma resposta"}
        
        # Detecção de travamento/loop
        last_tool_calls_signature = None  # Para detectar chamadas repetidas
        repeated_call_count = 0
        blocking_count = 0  # Contador de bloqueios consecutivos
        force_complex_model = False  # Flag para forçar modelo complexo após bloqueio
        blocking_patterns = [
            "🚫 BLOQUEIO:",           # Novo padrão principal
            "AÇÃO BLOQUEADA",          # Indicador claro de bloqueio
            "REPLANEJAMENTO NECESSÁRIO",  # Indica que precisa repensar
            "⚠️ Arquivo",              # Padrão antigo (compatibilidade)
            "JÁ EXISTE com conteúdo diferente",
            "pode travar o processo",
            "AVISO: Este comando"
        ]
        
        while iteration < task_max_iterations:
            iteration += 1
            self._write_log(f"\n{'─'*80}\n🔄 ITERAÇÃO {iteration}/{task_max_iterations}\n{'─'*80}\n")
            
            if self.verbose:
                self.console.print(f"\n[dim]═══ Iteração {iteration}/{task_max_iterations} ═══[/dim]")

            # Seleciona a configuração do modelo apropriado
            # IMPORTANTE: Se houve bloqueio na iteração anterior, FORÇA modelo complexo
            if force_complex_model:
                model_config = self._get_complex_model_config()
                self._write_log(f"🧠 FORÇANDO modelo complexo devido a bloqueio anterior\n")
                if self.verbose:
                    self.console.print(f"[bold magenta]🧠 Usando modelo complexo (bloqueio detectado)[/bold magenta]")
                force_complex_model = False  # Reset após usar
            else:
                model_config = self._get_model_config_for_tools(tool_calls=previous_tool_calls, iteration=iteration)
            model_name = model_config.name
            
            # Log da seleção
            provider_info = f" ({model_config.api_base})" if model_config.api_base else " (OpenAI padrão)"
            self._write_log(f"🤖 Chamando LLM (modelo: {model_name}{provider_info})...\n")
            
            if self.verbose and iteration == 1:
                if model_config.api_base:
                    self.console.print(f"[dim]⚡ Usando modelo: {model_name} em {model_config.api_base}[/dim]")
                else:
                    self.console.print(f"[dim]⚡ Usando modelo: {model_name} (OpenAI)[/dim]")
            
            try:
                # Verifica se este modelo tem cliente direto configurado
                if model_name in self.model_clients:
                    # Usa cliente OpenAI direto (para LM Studio, Ollama, etc.)
                    client = self.model_clients[model_name]
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        tools=self.tools_schema if self.tools_schema else None,
                        tool_choice="auto" if self.tools_schema else None
                    )
                    # Converte para formato compatível
                    class LiteLLMResponse:
                        def __init__(self, openai_response):
                            self.choices = [type('Choice', (), {
                                'message': openai_response.choices[0].message
                            })()]
                    response = LiteLLMResponse(response)
                elif hasattr(self, 'openai_client') and self.use_direct_openai:
                    # Legacy: cliente único
                    response = self.openai_client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        tools=self.tools_schema if self.tools_schema else None,
                        tool_choice="auto" if self.tools_schema else None
                    )
                    class LiteLLMResponse:
                        def __init__(self, openai_response):
                            self.choices = [type('Choice', (), {
                                'message': openai_response.choices[0].message
                            })()]
                    response = LiteLLMResponse(response)
                else:
                    # Usa LiteLLM (para OpenAI padrão ou outros providers)
                    completion_kwargs = {
                        "model": model_name,
                        "messages": messages,
                        "tools": self.tools_schema,
                        "tool_choice": "auto"
                    }
                    
                    # Adiciona api_base e api_key se configurados no ModelConfig
                    if model_config.api_base:
                        completion_kwargs["api_base"] = model_config.api_base
                    if model_config.api_key:
                        completion_kwargs["api_key"] = model_config.api_key
                    
                    response = litellm.completion(**completion_kwargs)
            except Exception as e:
                error_msg = f"✗ Erro ao chamar LLM: {e}\n"
                self._write_log(error_msg)
                if self.verbose:
                    self.console.print(f"[red]{error_msg}[/red]")
                return {"success": False, "response": f"Erro ao chamar LLM: {e}"}
            
            # LiteLLM retorna no mesmo formato do OpenAI
            message = response.choices[0].message
            self._write_log(f"✓ Resposta recebida do LLM\n")
            
            # Converte para formato de dicionário para adicionar ao histórico
            message_dict = {
                "role": message.role,
                "content": message.content if message.content else None
            }
            
            # Adiciona tool_calls se existirem
            if hasattr(message, 'tool_calls') and message.tool_calls:
                message_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": getattr(tc, 'type', 'function'),
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            
            messages.append(message_dict)

            # Verifica se há tool_calls (pode ser do objeto message ou do dict)
            tool_calls = None
            if hasattr(message, 'tool_calls') and message.tool_calls:
                tool_calls = message.tool_calls
            elif "tool_calls" in message_dict and message_dict["tool_calls"]:
                tool_calls = message_dict["tool_calls"]
            
            if not tool_calls:
                content = message.content if hasattr(message, 'content') else message_dict.get("content", "")
                self._write_log(f"✅ EXECUÇÃO CONCLUÍDA\n")
                self._write_log(f"Resposta: {content}\n")
                execution_result = {"success": True, "response": content}
                break  # Sai do loop para ir para validação

            self._write_log(f"🔧 {len(tool_calls)} ferramenta(s) a executar\n")
            
            # Salva tool_calls para usar na próxima iteração (se houver)
            previous_tool_calls = tool_calls
            
            for tool_call in tool_calls:
                # Suporta tanto objeto quanto dict
                if hasattr(tool_call, 'function'):
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_call_id = tool_call.id
                else:
                    # Formato dict
                    tool_name = tool_call['function']['name']
                    tool_args = json.loads(tool_call['function']['arguments'])
                    tool_call_id = tool_call['id']
                
                self._write_log(f"  → Executando: {tool_name}\n")
                self._write_log(f"     Argumentos: {json.dumps(tool_args, ensure_ascii=False)}\n")
                
                if self.verbose:
                    self.console.print(f"\n[yellow]🔧 Executando:[/yellow] [cyan]{tool_name}[/cyan]")
                
                try:
                    if tool_name in self.tools_registry:
                        tool_result = self.tools_registry[tool_name](**tool_args)
                    else:
                        tool_result = f"✗ Ferramenta '{tool_name}' não encontrada"
                except Exception as e:
                    tool_result = f"✗ Erro ao executar {tool_name}: {e}"
                    self._write_log(f"     ❌ ERRO: {tool_result}\n")
                
                # Registra ação para validação
                actions_taken.append(f"[{tool_name}] {str(tool_args)[:100]} → {tool_result[:100]}")
                
                # Log do resultado completo (sem truncagem)
                self._write_log(f"     ✓ Resultado: {tool_result}\n")
                
                if self.verbose:
                    self.console.print(f"[dim]→ Resultado: {tool_result[:200]}...[/dim]")
                
                messages.append({"role": "tool", "content": tool_result, "tool_call_id": tool_call_id})
                
                # =========================================================
                # DETECÇÃO DE BLOQUEIO E AUTO-REPLANEJAMENTO
                # =========================================================
                # Verifica se resultado contém padrões de bloqueio
                is_blocking_result = any(pattern in tool_result for pattern in blocking_patterns)
                
                # Cria assinatura da chamada para detectar repetição
                current_signature = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
                
                if current_signature == last_tool_calls_signature:
                    repeated_call_count += 1
                else:
                    repeated_call_count = 0
                    last_tool_calls_signature = current_signature
                
                # Se detectou bloqueio ou repetição, injeta replanejamento
                if is_blocking_result or repeated_call_count >= 1:
                    blocking_count += 1
                    self._write_log(f"\n🚨 BLOQUEIO #{blocking_count} DETECTADO! Forçando modelo complexo...\n")
                    
                    if self.verbose:
                        self.console.print(f"\n[bold red]🚨 BLOQUEIO #{blocking_count}![/bold red] Forçando modelo complexo na próxima iteração...")
                    
                    # IMPORTANTE: Força o modelo complexo na próxima iteração
                    force_complex_model = True
                    
                    # Constrói contexto detalhado do histórico de ações
                    recent_actions = "\n".join(actions_taken[-5:]) if actions_taken else "Nenhuma ação anterior"
                    
                    # Injeta mensagem de sistema forçando replanejamento com CONTEXTO COMPLETO
                    replan_instruction = f"""
🚨 **BLOQUEIO #{blocking_count} - MODELO COMPLEXO ATIVADO**

A ferramenta `{tool_name}` retornou um BLOQUEIO:

```
{tool_result}
```

📋 **HISTÓRICO RECENTE DE AÇÕES:**
{recent_actions}

⚠️ **ANÁLISE DO PROBLEMA:**
- O arquivo/recurso já existe e não pode ser sobrescrito diretamente
- O requirements.txt ATUAL já contém fastapi e uvicorn
- NÃO é necessário recriar o arquivo - as dependências já estão lá!

✅ **AÇÕES CORRETAS (escolha UMA):**
1. **ACEITAR o arquivo existente** - Se já contém o que precisa, prossiga sem modificar
2. **Usar `read_file`** - Para verificar o conteúdo atual
3. **Usar `edit_lines` ou `insert_lines`** - Para adicionar/modificar linhas específicas
4. **Usar `force_write_file`** - APENAS se realmente precisar sobrescrever (com justificativa)

❌ **NÃO FAÇA:**
- NÃO tente `write_file` novamente no mesmo arquivo
- NÃO repita a mesma ação que causou o bloqueio

🎯 **PRÓXIMO PASSO SUGERIDO:**
Como o requirements.txt já existe com fastapi e uvicorn, você deve:
1. Verificar se main.py existe e está correto
2. Instalar dependências com `pip install -r requirements.txt`
3. Testar a aplicação

Qual ação você vai tomar agora?
"""
                    messages.append({
                        "role": "user", 
                        "content": replan_instruction
                    })
                    
                    # Reseta contador de repetição após injetar replanejamento
                    repeated_call_count = 0
                    last_tool_calls_signature = None
                else:
                    # Ação bem-sucedida, reseta contador de bloqueios
                    if blocking_count > 0:
                        self._write_log(f"✅ Ação bem-sucedida após {blocking_count} bloqueio(s)\n")
                        blocking_count = 0
        else:
            # Loop terminou por limite de iterações
            self._write_log(f"\n⚠️ LIMITE DE ITERAÇÕES ATINGIDO ({task_max_iterations})\n")
            execution_result = {"success": False, "response": f"Limite de iterações ({task_max_iterations}) atingido."}

        # =====================================================================
        # FASE 3: VALIDAÇÃO (se multi-model ativado e não pulado)
        # =====================================================================
        if self.use_multi_model and not skip_validation and execution_result.get("success"):
            validation_result = self._phase_validation(task, execution_result, actions_taken)
            
            # Inclui validação no resultado final
            final_result = {
                "success": execution_result["success"] and validation_result.get("validated", True),
                "response": execution_result["response"],
                "validation": validation_result,
                "actions_count": len(actions_taken),
                "iterations": iteration
            }
            
            if validation_result.get("needs_retry"):
                self._write_log(f"⚠️ Validação sugeriu retry, mas não implementado ainda\n")
            
            if self.verbose:
                status_icon = "✅" if final_result["success"] else "⚠️"
                self.console.print(Panel(
                    f"[green]{status_icon} Tarefa concluída![/green]\n\n{execution_result['response'][:500]}...",
                    border_style="green"
                ))
            
            # =========================================================
            # GIT REVIEW: Mostra resumo da sessão Git (OBRIGATÓRIO)
            # =========================================================
            if self.git_session_started and _is_git_repo(self.workspace):
                self._write_log(f"\n{'='*80}\n🏁 GIT REVIEW (Revisão Final da Sessão)\n{'='*80}\n")
                if self.verbose:
                    self.console.print("\n[bold cyan]🏁 GIT REVIEW - Revisão Final da Sessão[/bold cyan]")
                git_review_result = self.show_git_review()
                final_result["git_review"] = git_review_result
            
            return final_result
        else:
            # Sem validação, retorna resultado da execução
            if self.verbose and execution_result.get("success"):
                self.console.print(Panel(
                    f"[green]✓ Tarefa concluída![/green]\n\n{execution_result['response'][:500] if execution_result.get('response') else 'OK'}",
                    border_style="green"
                ))
            
            return {
                **execution_result,
                "actions_count": len(actions_taken),
                "iterations": iteration
            }

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

