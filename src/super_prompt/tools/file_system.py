"""
File system tools for the Modern AI Agent.
"""
from pathlib import Path
from typing import List
from .tool_decorator import tool
from ..code_agent import CodeAgent

@tool(
    description="Lê o conteúdo completo de um arquivo do workspace",
    parameters={"filepath": {"type": "string", "description": "Caminho relativo do arquivo no workspace"}},
    required=["filepath"],
    complexity="simple"
)
def read_file(filepath: str, code_agent: CodeAgent, workspace: Path) -> str:
    """Lê um arquivo"""
    try:
        content = code_agent.read_file(filepath)
        return f"✓ Conteúdo de {filepath}:\n\n{content}"
    except Exception as e:
        return f"✗ Erro ao ler {filepath}: {e}"

@tool(
    description="Cria um novo arquivo. BLOQUEIA se arquivo já existe (proteção). Para sobrescrever use force_write_file.",
    parameters={
        "filepath": {"type": "string", "description": "Caminho do arquivo a criar"},
        "content": {"type": "string", "description": "Conteúdo completo a escrever"}
    },
    required=["filepath", "content"],
    complexity="simple"
)
def write_file(filepath: str, content: str, code_agent: CodeAgent, workspace: Path) -> str:
    """Escreve um arquivo COM VERIFICAÇÃO."""
    try:
        file_path = workspace / filepath
        if file_path.exists():
            return f"⚠️ ATENÇÃO: Arquivo '{filepath}' JÁ EXISTE! Use 'force_write_file' para sobrescrever."
        code_agent.write_file(filepath, content, show_preview=False)
        return f"✓ Arquivo {filepath} CRIADO com sucesso."
    except Exception as e:
        return f"✗ Erro ao escrever {filepath}: {e}"

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
def force_write_file(filepath: str, content: str, reason: str, code_agent: CodeAgent, workspace: Path) -> str:
    """Sobrescreve arquivo forçadamente."""
    try:
        file_path = workspace / filepath
        if not file_path.exists():
            return f"⚠️ Arquivo '{filepath}' NÃO EXISTE. Use 'write_file' para criar."
        code_agent.create_backup(filepath)
        code_agent.write_file(filepath, content, show_preview=False)
        return f"✓ Arquivo {filepath} SOBRESCRITO com sucesso. Motivo: {reason}"
    except Exception as e:
        return f"✗ Erro ao sobrescrever {filepath}: {e}"

@tool(
    description="Lista arquivos no workspace com um padrão glob",
    parameters={"pattern": {"type": "string", "description": "Padrão glob (ex: '*.py', '**/*.js')", "default": "*"}},
    required=[],
    complexity="simple"
)
def list_files(code_agent: CodeAgent, workspace: Path, pattern: str = "*") -> str:
    """Lista arquivos"""
    try:
        if "**" in pattern:
            files = list(workspace.rglob(pattern.replace("**/", "")))
        else:
            files = list(workspace.glob(pattern))
        files = [f for f in files if f.is_file()]
        files = [f for f in files if ".code_agent_backups" not in str(f)]
        if not files:
            return f"Nenhum arquivo encontrado: {pattern}"
        return f"✓ Arquivos encontrados ({len(files)}):\n" + "\n".join(f"  - {f}" for f in files[:50])
    except Exception as e:
        return f"✗ Erro ao listar: {e}"

@tool(
    description="Mostra um arquivo com syntax highlighting",
    parameters={"filepath": {"type": "string", "description": "Caminho do arquivo"}},
    required=["filepath"],
    complexity="simple"
)
def show_file(filepath: str, code_agent: CodeAgent, workspace: Path) -> str:
    """Mostra arquivo"""
    try:
        content = code_agent.read_file(filepath)
        lines = content.splitlines()
        preview = "\n".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines[:30]))
        more = f"\n... ({len(lines) - 30} linhas restantes)" if len(lines) > 30 else ""
        return f"✓ Preview de {filepath} ({len(lines)} linhas):\n\n{preview}{more}"
    except Exception as e:
        return f"✗ Erro: {e}"
