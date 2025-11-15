"""
Toolkit for the Modern AI Agent.

This module contains all the functions that the agent can execute.
Tools are registered using the `@tool` decorator.
"""
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

from .code_agent import CodeAgent
from .tool_decorator import tool

class ToolManager:
    def __init__(self, workspace: Path, code_agent: CodeAgent):
        self.workspace = workspace
        self.code_agent = code_agent

    @tool(
        description="SEMPRE use isto ANTES de criar/modificar arquivo. Verifica se arquivo existe e sugere a melhor ação (criar, editar, ou usar outro nome).",
        parameters={
            "filepath": {"type": "string", "description": "Caminho do arquivo que você quer criar ou modificar"},
            "intended_action": {"type": "string", "description": "O que você pretende fazer (ex: 'criar app fastapi', 'adicionar rota', 'corrigir bug')"}
        },
        required=["filepath", "intended_action"],
        complexity="complex"
    )
    def check_file_and_suggest_action(self, filepath: str, intended_action: str) -> str:
        return self._tool_check_file_and_suggest(filepath, intended_action)

    @tool(
        description="Lê o conteúdo completo de um arquivo do workspace",
        parameters={"filepath": {"type": "string", "description": "Caminho relativo do arquivo no workspace"}},
        required=["filepath"],
        complexity="simple"
    )
    def read_file(self, filepath: str) -> str:
        return self._tool_read_file(filepath)

    @tool(
        description="Cria um novo arquivo. BLOQUEIA se arquivo já existe (proteção). Para sobrescrever use force_write_file.",
        parameters={
            "filepath": {"type": "string", "description": "Caminho do arquivo a criar"},
            "content": {"type": "string", "description": "Conteúdo completo a escrever"}
        },
        required=["filepath", "content"],
        complexity="simple"
    )
    def write_file(self, filepath: str, content: str) -> str:
        return self._tool_write_file(filepath, content)

    @tool(
        description="Sobrescreve um arquivo EXISTENTE forçadamente. Use APENAS quando tiver certeza. Cria backup automático.",
        parameters={
            "filepath": {"type": "string", "description": "Caminho do arquivo a sobrescrever"},
            "content": {"type": "string", "description": "Novo conteúdo completo"},
            "reason": {"type": "string", "description": "Motivo da sobrescrita (obrigatório para audit)"}
        },
        required=["filepath", "content", "reason"],
        complexity="simple"
    )
    def force_write_file(self, filepath: str, content: str, reason: str) -> str:
        return self._tool_force_write_file(filepath, content, reason)

    @tool(
        description="Busca e substitui texto em um arquivo",
        parameters={
            "filepath": {"type": "string", "description": "Caminho do arquivo"},
            "search": {"type": "string", "description": "Texto exato a buscar"},
            "replace": {"type": "string", "description": "Texto substituto"}
        },
        required=["filepath", "search", "replace"],
        complexity="simple"
    )
    def search_replace(self, filepath: str, search: str, replace: str) -> str:
        return self._tool_search_replace(filepath, search, replace)

    @tool(
        description="Edita linhas específicas de um arquivo (1-indexed)",
        parameters={
            "filepath": {"type": "string", "description": "Caminho do arquivo"},
            "start_line": {"type": "integer", "description": "Linha inicial (1-indexed)"},
            "end_line": {"type": "integer", "description": "Linha final (1-indexed, inclusiva)"},
            "new_content": {"type": "string", "description": "Novo conteúdo para as linhas"}
        },
        required=["filepath", "start_line", "end_line", "new_content"],
        complexity="simple"
    )
    def edit_lines(self, filepath: str, start_line: int, end_line: int, new_content: str) -> str:
        return self._tool_edit_lines(filepath, start_line, end_line, new_content)

    @tool(
        description="🗑️ Remove linhas específicas de um arquivo. Suporta range (start_line-end_line) ou lista de índices (line_indices).",
        parameters={
            "filepath": {"type": "string", "description": "Caminho do arquivo"},
            "start_line": {"type": "integer", "description": "Linha inicial do range (1-indexed, inclusiva). Use com end_line para remover range."}, 
            "end_line": {"type": "integer", "description": "Linha final do range (1-indexed, inclusiva). Use com start_line para remover range."}, 
            "line_indices": {"type": "array", "items": {"type": "integer"}, "description": "Lista de índices de linhas para remover (0-indexed). Ex: [0, 10, 23] remove linhas 1, 11, 24. Use este OU start_line/end_line."}
        },
        required=["filepath"],
        complexity="simple"
    )
    def delete_lines(self, filepath: str, start_line: Optional[int] = None, end_line: Optional[int] = None, line_indices: Optional[List[int]] = None) -> str:
        return self._tool_delete_lines(filepath, start_line, end_line, line_indices)

    @tool(
        description="Lista arquivos no workspace com um padrão glob",
        parameters={"pattern": {"type": "string", "description": "Padrão glob (ex: '*.py', '**/*.js')", "default": "*"}},
        required=[],
        complexity="simple"
    )
    def list_files(self, pattern: str = "*") -> str:
        return self._tool_list_files(pattern)

    @tool(
        description="Mostra um arquivo com syntax highlighting",
        parameters={"filepath": {"type": "string", "description": "Caminho do arquivo"}},
        required=["filepath"],
        complexity="simple"
    )
    def show_file(self, filepath: str) -> str:
        return self._tool_show_file(filepath)

    @tool(
        description="Executa um comando shell único (ex: ls, pwd, git status). CUIDADO: use apenas comandos seguros de leitura.",
        parameters={
            "command": {"type": "string", "description": "Comando shell a executar (ex: 'ls -la', 'pwd', 'git status')"},
            "timeout": {"type": "integer", "description": "Timeout em segundos (padrão: 30)", "default": 30}
        },
        required=["command"],
        complexity="simple"
    )
    def run_command(self, command: str, timeout: int = 30) -> str:
        return self._tool_run_command(command, timeout)

    @tool(
        description="Executa um script shell completo (múltiplas linhas). Use para operações batch.",
        parameters={
            "script": {"type": "string", "description": "Script shell completo a executar"},
            "shell": {"type": "string", "description": "Shell a usar (bash, sh, zsh). Padrão: bash", "default": "bash"},
            "timeout": {"type": "integer", "description": "Timeout em segundos (padrão: 60)", "default": 60}
        },
        required=["script"],
        complexity="simple"
    )
    def run_script(self, script: str, shell: str = "bash", timeout: int = 60) -> str:
        return self._tool_run_script(script, shell, timeout)

    def _tool_check_file_and_suggest(self, filepath: str, intended_action: str) -> str:
        try:
            file_path = self.workspace / filepath
            if not file_path.exists():
                return (
                    f"✅ ARQUIVO NÃO EXISTE: '{filepath}'\n\n"
                    f"➡️ AÇÃO RECOMENDADA: **CRIAR ARQUIVO NOVO**\n\n"
                    f"Use: write_file('{filepath}', conteudo)\n\n"
                    f"Você pode criar este arquivo com segurança.\n"
                    f"Intenção: {intended_action}"
                )
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            lines_count = len(current_content.splitlines())
            chars_count = len(current_content)
            conflict_detected = False
            conflict_reason = ""
            suggested_alternative = ""
            if any(indicator in current_content.lower() for indicator in ['modernaiaagent', 'execute_task', 'code_agent', 'agent.execute', 'from modern_ai_agent']):
                conflict_detected = True
                conflict_reason = "Este arquivo é um SCRIPT DE TESTE/DEMO do próprio Modern AI Agent!"
                if 'fastapi' in intended_action.lower():
                    suggested_alternative = "fastapi_app.py ou main.py ou server.py"
                else:
                    suggested_alternative = f"main.py ou {filepath.replace('.py', '_app.py')}"
            file_info = f"⚠️ ARQUIVO JÁ EXISTE: '{filepath}'\n- Linhas: {lines_count}\n- Caracteres: {chars_count}\n"
            if conflict_detected:
                file_info += (
                    f"🔴 **CONFLITO DETECTADO!**\n"
                    f"❌ {conflict_reason}\n"
                    f"➡️ **AÇÃO RECOMENDADA: USE OUTRO NOME DE ARQUIVO**\n"
                    f"🎯 **SUGESTÕES DE NOMES:** {suggested_alternative}\n"
                )
            else:
                file_info += "➡️ **AÇÃO RECOMENDADA: EDITE O ARQUIVO EXISTENTE** ou use outro nome."
            return file_info
        except Exception as e:
            return f"✗ Erro ao verificar {filepath}: {e}"

    def _tool_read_file(self, filepath: str) -> str:
        try:
            content = self.code_agent.read_file(filepath)
            return f"✓ Conteúdo de {filepath}:\n\n{content}"
        except Exception as e:
            return f"✗ Erro ao ler {filepath}: {e}"

    def _tool_write_file(self, filepath: str, content: str) -> str:
        try:
            file_path = self.workspace / filepath
            if file_path.exists():
                return f"⚠️ ATENÇÃO: Arquivo '{filepath}' JÁ EXISTE! Use 'force_write_file' para sobrescrever."
            self.code_agent.write_file(filepath, content, show_preview=False)
            return f"✓ Arquivo {filepath} CRIADO com sucesso."
        except Exception as e:
            return f"✗ Erro ao escrever {filepath}: {e}"

    def _tool_force_write_file(self, filepath: str, content: str, reason: str) -> str:
        try:
            file_path = self.workspace / filepath
            if not file_path.exists():
                return f"⚠️ Arquivo '{filepath}' NÃO EXISTE. Use 'write_file' para criar."
            self.code_agent.create_backup(filepath)
            self.code_agent.write_file(filepath, content, show_preview=False)
            return f"✓ Arquivo {filepath} SOBRESCRITO com sucesso. Motivo: {reason}"
        except Exception as e:
            return f"✗ Erro ao sobrescrever {filepath}: {e}"

    def _tool_search_replace(self, filepath: str, search: str, replace: str) -> str:
        try:
            self.code_agent.search_replace(filepath, search, replace, show_preview=False)
            return f"✓ Substituição em {filepath} concluída"
        except Exception as e:
            return f"✗ Erro na substituição: {e}"

    def _tool_edit_lines(self, filepath: str, start_line: int, end_line: int, new_content: str) -> str:
        try:
            success = self.code_agent.edit_lines(filepath, start_line, end_line, new_content, show_preview=False)
            if not success:
                return f"❌ FALHA: edit_lines retornou False para {filepath}."
            return f"✓ Linhas {start_line}-{end_line} de {filepath} editadas com SUCESSO"
        except Exception as e:
            return f"❌ ERRO FATAL ao editar {filepath}: {e}"

    def _tool_delete_lines(self, filepath: str, start_line: Optional[int] = None, end_line: Optional[int] = None, line_indices: Optional[List[int]] = None) -> str:
        try:
            success = self.code_agent.delete_lines(filepath, start_line=start_line, end_line=end_line, line_indices=line_indices, show_preview=False)
            if not success:
                return f"❌ FALHA: delete_lines retornou False para {filepath}."
            return f"✓ Linhas removidas de {filepath} com SUCESSO"
        except Exception as e:
            return f"❌ ERRO FATAL ao deletar linhas de {filepath}: {e}"

    def _tool_list_files(self, pattern: str = "*") -> str:
        try:
            if "**" in pattern:
                files = list(self.workspace.rglob(pattern.replace("**/", "")))
            else:
                files = list(self.workspace.glob(pattern))
            files = [f.relative_to(self.workspace) for f in files if f.is_file()]
            files = [f for f in files if ".code_agent_backups" not in str(f)]
            if not files:
                return f"Nenhum arquivo encontrado: {pattern}"
            return f"✓ Arquivos encontrados ({len(files)}):\n" + "\n".join(f"  - {f}" for f in files[:50])
        except Exception as e:
            return f"✗ Erro ao listar: {e}"

    def _tool_show_file(self, filepath: str) -> str:
        try:
            content = self.code_agent.read_file(filepath)
            lines = content.splitlines()
            preview = "\n".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines[:30]))
            more = f"\n... ({len(lines) - 30} linhas restantes)" if len(lines) > 30 else ""
            return f"✓ Preview de {filepath} ({len(lines)} linhas):\n\n{preview}{more}"
        except Exception as e:
            return f"✗ Erro: {e}"

    def _tool_run_command(self, command: str, timeout: int = 30) -> str:
        dangerous_commands = ['rm -rf', 'mkfs', 'dd', ':(){:|:&};:', 'fork bomb', '/dev/sda', 'mv / ', 'chmod -R 777 /', '> /dev/sda', 'wget http', 'curl http']
        if any(d in command for d in dangerous_commands):
            return f"✗ BLOQUEADO: Comando potencialmente perigoso detectado."
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            output = f"✓ Comando executado: {command}\nExit code: {result.returncode}\n"
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            return output
        except subprocess.TimeoutExpired:
            return f"✗ TIMEOUT: Comando excedeu {timeout}s de execução"
        except Exception as e:
            return f"✗ Erro ao executar comando: {e}"

    def _tool_run_script(self, script: str, shell: str = "bash", timeout: int = 60) -> str:
        allowed_shells = ['bash', 'sh', 'zsh', 'dash']
        if shell not in allowed_shells:
            return f"✗ Shell não permitido: {shell}. Use: {', '.join(allowed_shells)}"
        dangerous_patterns = ['rm -rf /', 'rm -rf *', 'mkfs', 'dd if=', 'dd of=/dev', ':(){:|:&};:', '> /dev/sda', 'chmod -R 777 /', 'wget http://', 'curl http://']
        if any(d in script for d in dangerous_patterns):
            return f"✗ BLOQUEADO: Padrão perigoso detectado no script."
        try:
            result = subprocess.run([shell, '-c', script], cwd=str(self.workspace), capture_output=True, text=True, timeout=timeout)
            output = f"✓ Script {shell} executado\nExit code: {result.returncode}\n"
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            return output
        except subprocess.TimeoutExpired:
            return f"✗ TIMEOUT: Script excedeu {timeout}s de execução"
        except FileNotFoundError:
            return f"✗ Shell não encontrado: {shell}"
        except Exception as e:
            return f"✗ Erro ao executar script: {e}"