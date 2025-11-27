"""
Code editing tools for the Modern AI Agent.

Supports optional Git checkpoints for safe versioning.
"""
from pathlib import Path
from typing import Optional, List
from .tool_decorator import tool
from ..code_agent import CodeAgent
from .git_tools import create_checkpoint_if_requested

@tool(
    description="""Busca e substitui texto em um arquivo.

🔖 CHECKPOINT: Use checkpoint="mensagem" para criar um ponto de restauração Git após a operação.""",
    parameters={
        "filepath": {"type": "string", "description": "Caminho do arquivo"},
        "search": {"type": "string", "description": "Texto exato a buscar"},
        "replace": {"type": "string", "description": "Texto substituto"},
        "checkpoint": {"type": "string", "description": "Se fornecido, cria um checkpoint Git após a operação"}
    },
    required=["filepath", "search", "replace"],
    complexity="simple"
)
def search_replace(filepath: str, search: str, replace: str, code_agent: CodeAgent, workspace: Path, checkpoint: Optional[str] = None) -> str:
    """Busca e substitui"""
    try:
        code_agent.search_replace(filepath, search, replace, show_preview=False)
        result = f"✓ Substituição em {filepath} concluída"
        
        # Cria checkpoint se solicitado
        checkpoint_msg = create_checkpoint_if_requested(workspace, checkpoint, "search_replace", filepath)
        if checkpoint_msg:
            result += f"\n{checkpoint_msg}"
        
        return result
    except Exception as e:
        return f"✗ Erro na substituição: {e}"

@tool(
    description="""Edita linhas específicas de um arquivo (1-indexed).

🔖 CHECKPOINT: Use checkpoint="mensagem" para criar um ponto de restauração Git após a operação.""",
    parameters={
        "filepath": {"type": "string", "description": "Caminho do arquivo"},
        "start_line": {"type": "integer", "description": "Linha inicial (1-indexed)"},
        "end_line": {"type": "integer", "description": "Linha final (1-indexed, inclusiva)"},
        "new_content": {"type": "string", "description": "Novo conteúdo para as linhas"},
        "checkpoint": {"type": "string", "description": "Se fornecido, cria um checkpoint Git após a operação"}
    },
    required=["filepath", "start_line", "end_line", "new_content"],
    complexity="simple"
)
def edit_lines(filepath: str, start_line: int, end_line: int, new_content: str, code_agent: CodeAgent, workspace: Path, checkpoint: Optional[str] = None) -> str:
    """Edita/SUBSTITUI linhas de um arquivo."""
    try:
        success = code_agent.edit_lines(filepath, start_line, end_line, new_content, show_preview=False)
        if not success:
            return f"❌ FALHA: edit_lines retornou False para {filepath}."
        result = f"✓ Linhas {start_line}-{end_line} de {filepath} editadas com SUCESSO"
        
        # Cria checkpoint se solicitado
        checkpoint_msg = create_checkpoint_if_requested(workspace, checkpoint, "edit_lines", filepath)
        if checkpoint_msg:
            result += f"\n{checkpoint_msg}"
        
        return result
    except Exception as e:
        return f"❌ ERRO FATAL ao editar {filepath}: {e}"

@tool(
    description="""🆕 CRÍTICO! INSERE código APÓS uma linha (não substitui). Use quando quiser ADICIONAR código novo sem remover existente.

🔖 CHECKPOINT: Use checkpoint="mensagem" para criar um ponto de restauração Git após a operação.""",
    parameters={
        "filepath": {"type": "string", "description": "Arquivo onde inserir"},
        "after_line": {"type": "integer", "description": "Insere APÓS esta linha (ex: after_line=8 insere entre linha 8 e 9)"},
        "content": {"type": "string", "description": "Conteúdo a inserir"},
        "checkpoint": {"type": "string", "description": "Se fornecido, cria um checkpoint Git após a operação"}
    },
    required=["filepath", "after_line", "content"],
    complexity="simple"
)
def insert_lines(filepath: str, after_line: int, content: str, code_agent: CodeAgent, workspace: Path, checkpoint: Optional[str] = None) -> str:
    """INSERE código APÓS uma linha específica (não substitui nada)."""
    try:
        file_content = code_agent.read_file(filepath)
        lines = file_content.splitlines(keepends=True)
        total_lines = len(lines)
        if after_line < 0 or after_line > total_lines:
            return f"❌ FALHA: after_line={after_line} está fora dos limites do arquivo (0-{total_lines})."
        if content and not content.endswith('\n'):
            content += '\n'
        new_lines = lines[:after_line] + [content] + lines[after_line:]
        new_content_str = ''.join(new_lines)
        code_agent.create_backup(filepath)
        with open(workspace / filepath, 'w', encoding='utf-8') as f:
            f.write(new_content_str)
        result = f"✅ SUCESSO: Código INSERIDO APÓS linha {after_line} em {filepath}"
        
        # Cria checkpoint se solicitado
        checkpoint_msg = create_checkpoint_if_requested(workspace, checkpoint, "insert_lines", filepath)
        if checkpoint_msg:
            result += f"\n{checkpoint_msg}"
        
        return result
    except Exception as e:
        return f"❌ ERRO ao inserir linhas: {e}"

@tool(
    description="""🗑️ Remove linhas específicas de um arquivo. Suporta range (start_line-end_line) ou lista de índices (line_indices).

🔖 CHECKPOINT: Use checkpoint="mensagem" para criar um ponto de restauração Git após a operação.""",
    parameters={
        "filepath": {"type": "string", "description": "Caminho do arquivo"},
        "start_line": {"type": "integer", "description": "Linha inicial do range (1-indexed, inclusiva)."},
        "end_line": {"type": "integer", "description": "Linha final do range (1-indexed, inclusiva)."},
        "line_indices": {"type": "array", "items": {"type": "integer"}, "description": "Lista de índices de linhas para remover (0-indexed)."},
        "checkpoint": {"type": "string", "description": "Se fornecido, cria um checkpoint Git após a operação"}
    },
    required=["filepath"],
    complexity="simple"
)
def delete_lines(filepath: str, code_agent: CodeAgent, workspace: Path, start_line: Optional[int] = None, end_line: Optional[int] = None, line_indices: Optional[List[int]] = None, checkpoint: Optional[str] = None) -> str:
    """Remove linhas específicas de um arquivo."""
    try:
        success = code_agent.delete_lines(filepath, start_line=start_line, end_line=end_line, line_indices=line_indices, show_preview=False)
        if not success:
            return f"❌ FALHA: delete_lines retornou False para {filepath}."
        result = f"✓ Linhas removidas de {filepath} com SUCESSO"
        
        # Cria checkpoint se solicitado
        checkpoint_msg = create_checkpoint_if_requested(workspace, checkpoint, "delete_lines", filepath)
        if checkpoint_msg:
            result += f"\n{checkpoint_msg}"
        
        return result
    except Exception as e:
        return f"❌ ERRO FATAL ao deletar linhas de {filepath}: {e}"
