"""
Git version control tools for the Modern AI Agent.

Provides checkpoint, rollback, stash, and branch management for safe code editing.
Uses Rich library for beautiful terminal output.
"""
import subprocess
import os
from io import StringIO
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from .tool_decorator import tool

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box


def _render_to_string(renderable) -> str:
    """Renderiza um objeto Rich para string, capturando a saída."""
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True, width=80)
    console.print(renderable)
    return string_io.getvalue()

# ============================================================================
# UTILITY FUNCTIONS (Not exposed as tools)
# ============================================================================

def _run_git(command: str, workspace: Path, check: bool = True) -> tuple[bool, str, str]:
    """
    Executa um comando git e retorna (sucesso, stdout, stderr).
    
    Args:
        command: Comando git (sem 'git' no início)
        workspace: Diretório do workspace
        check: Se True, considera exit code != 0 como falha
        
    Returns:
        Tuple (sucesso, stdout, stderr)
    """
    try:
        result = subprocess.run(
            f"git {command}",
            shell=True,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=30
        )
        success = result.returncode == 0 if check else True
        return success, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Timeout ao executar comando git"
    except Exception as e:
        return False, "", str(e)


def _is_git_repo(workspace: Path) -> bool:
    """Verifica se o workspace é um repositório Git."""
    success, _, _ = _run_git("rev-parse --is-inside-work-tree", workspace, check=False)
    return success


def _has_changes(workspace: Path) -> bool:
    """Verifica se há mudanças não commitadas."""
    success, stdout, _ = _run_git("status --porcelain", workspace)
    return bool(stdout.strip()) if success else False


def _get_current_branch(workspace: Path) -> str:
    """Retorna o nome da branch atual."""
    success, stdout, _ = _run_git("branch --show-current", workspace)
    return stdout if success else "unknown"


def _format_file_status(status_line: str) -> str:
    """Formata uma linha de status do git para exibição."""
    if not status_line or len(status_line) < 3:
        return status_line
    
    status_code = status_line[:2]
    filename = status_line[3:]
    
    status_map = {
        'M ': '✏️  modificado (staged)',
        ' M': '✏️  modificado',
        'A ': '🆕 novo (staged)',
        '??': '❓ não rastreado',
        'D ': '🗑️  deletado (staged)',
        ' D': '🗑️  deletado',
        'R ': '📝 renomeado',
        'C ': '📋 copiado',
        'MM': '✏️  modificado (staged + local)',
        'AM': '🆕 novo (staged) + modificado',
    }
    
    icon = status_map.get(status_code, f'[{status_code}]')
    return f"  {icon}: {filename}"


# ============================================================================
# GIT INITIALIZATION
# ============================================================================

@tool(
    description="""Inicializa um repositório Git no workspace se ainda não existir.
    
Use esta ferramenta no início de uma sessão para garantir que o versionamento está ativo.""",
    parameters={
        "initial_commit": {
            "type": "boolean", 
            "description": "Se True, cria um commit inicial com todos os arquivos existentes",
            "default": True
        }
    },
    required=[],
    complexity="simple"
)
def git_init(workspace: Path, initial_commit: bool = True) -> str:
    """Inicializa repositório Git."""
    
    if _is_git_repo(workspace):
        branch = _get_current_branch(workspace)
        return f"ℹ️ Repositório Git já existe no workspace.\n📍 Branch atual: {branch}"
    
    # Inicializa repositório
    success, stdout, stderr = _run_git("init", workspace)
    if not success:
        return f"❌ Erro ao inicializar Git: {stderr}"
    
    output = "✅ Repositório Git inicializado com sucesso!\n"
    
    # Cria .gitignore se não existir
    gitignore_path = workspace / ".gitignore"
    if not gitignore_path.exists():
        default_gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
.env
venv/
.venv/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Logs
*.log
logs/

# Backups do Code Agent
.code_agent_backups/

# OS
.DS_Store
Thumbs.db
"""
        with open(gitignore_path, 'w') as f:
            f.write(default_gitignore)
        output += "📄 Arquivo .gitignore criado com configurações padrão\n"
    
    # Commit inicial
    if initial_commit:
        _run_git("add -A", workspace)
        success, _, stderr = _run_git('commit -m "🎉 Commit inicial"', workspace)
        if success:
            output += "📦 Commit inicial criado com todos os arquivos\n"
        else:
            output += f"⚠️ Não foi possível criar commit inicial: {stderr}\n"
    
    return output


# ============================================================================
# CHECKPOINT SYSTEM
# ============================================================================

@tool(
    description="""🔖 Cria um CHECKPOINT (commit) para salvar o estado atual do código.

Use esta ferramenta:
- Antes de fazer mudanças arriscadas
- Após completar uma funcionalidade
- Para criar pontos de restauração

O checkpoint permite reverter facilmente com git_rollback().""",
    parameters={
        "message": {
            "type": "string", 
            "description": "Mensagem descritiva do checkpoint (ex: 'antes de refatorar auth')"
        },
        "add_all": {
            "type": "boolean",
            "description": "Se True, adiciona todos os arquivos modificados ao checkpoint",
            "default": True
        }
    },
    required=["message"],
    complexity="simple"
)
def git_checkpoint(message: str, workspace: Path, add_all: bool = True) -> str:
    """Cria um checkpoint (commit) nomeado."""
    
    if not _is_git_repo(workspace):
        return "❌ Workspace não é um repositório Git. Use git_init() primeiro."
    
    # Verifica se há mudanças
    if not _has_changes(workspace):
        return "ℹ️ Nenhuma mudança para criar checkpoint. Working directory está limpo."
    
    # Adiciona arquivos
    if add_all:
        success, _, stderr = _run_git("add -A", workspace)
        if not success:
            return f"❌ Erro ao adicionar arquivos: {stderr}"
    
    # Cria timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_message = f"🔖 [CHECKPOINT] {message} ({timestamp})"
    
    # Cria commit
    success, stdout, stderr = _run_git(f'commit -m "{commit_message}"', workspace)
    if not success:
        return f"❌ Erro ao criar checkpoint: {stderr}"
    
    # Obtém hash do commit
    success, commit_hash, _ = _run_git("rev-parse --short HEAD", workspace)
    
    return (
        f"✅ Checkpoint criado com sucesso!\n\n"
        f"🔖 Hash: {commit_hash}\n"
        f"📝 Mensagem: {message}\n"
        f"⏰ Timestamp: {timestamp}\n\n"
        f"💡 Para reverter: git_rollback(\"{commit_hash}\")"
    )


@tool(
    description="""⏪ Reverte o código para um checkpoint anterior.

MODOS DE OPERAÇÃO:
1. Soft (padrão): Mantém arquivos modificados, apenas move o HEAD
2. Hard: Descarta TODAS as mudanças e volta ao estado exato do checkpoint

⚠️ CUIDADO: O modo 'hard' é IRREVERSÍVEL e descarta todas as mudanças não commitadas!""",
    parameters={
        "ref": {
            "type": "string",
            "description": "Hash do commit ou referência (ex: 'abc123', 'HEAD~1', 'HEAD~2')"
        },
        "hard": {
            "type": "boolean",
            "description": "Se True, descarta todas as mudanças (IRREVERSÍVEL). Se False, mantém mudanças locais.",
            "default": False
        },
        "files": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Lista de arquivos específicos para reverter (opcional). Se vazio, reverte tudo."
        }
    },
    required=["ref"],
    complexity="simple"
)
def git_rollback(ref: str, workspace: Path, hard: bool = False, files: Optional[List[str]] = None) -> str:
    """Reverte para um checkpoint anterior."""
    
    if not _is_git_repo(workspace):
        return "❌ Workspace não é um repositório Git."
    
    # Se arquivos específicos foram passados, faz checkout parcial
    if files:
        results = []
        for filepath in files:
            success, _, stderr = _run_git(f"checkout {ref} -- {filepath}", workspace)
            if success:
                results.append(f"  ✅ {filepath}")
            else:
                results.append(f"  ❌ {filepath}: {stderr}")
        
        return (
            f"📂 Rollback parcial para {ref}:\n\n" +
            "\n".join(results) +
            f"\n\n💡 Arquivos restaurados do checkpoint {ref}"
        )
    
    # Rollback completo
    mode = "--hard" if hard else "--soft"
    warning = "⚠️ MODO HARD: Mudanças locais foram DESCARTADAS!" if hard else "ℹ️ Modo soft: Mudanças locais preservadas"
    
    # Salva estado atual antes (se não for hard)
    if not hard:
        _run_git("stash push -m 'auto-backup before rollback'", workspace)
    
    success, stdout, stderr = _run_git(f"reset {mode} {ref}", workspace)
    
    if not success:
        return f"❌ Erro no rollback: {stderr}"
    
    # Obtém info do commit atual
    success, commit_info, _ = _run_git("log -1 --oneline", workspace)
    
    return (
        f"✅ Rollback realizado com sucesso!\n\n"
        f"📍 Agora em: {commit_info}\n"
        f"{warning}\n\n"
        f"💡 Para desfazer este rollback:\n"
        f"   - Se soft: git_rollback('ORIG_HEAD')\n"
        f"   - Se tinha stash: git_stash_apply()"
    )


# ============================================================================
# STASH SYSTEM
# ============================================================================

@tool(
    description="""💾 Salva as mudanças atuais em um STASH (área temporária).

Use quando quiser:
- Guardar trabalho em andamento para retomar depois
- Testar algo sem perder mudanças atuais
- Trocar de branch sem commitar

O stash é uma pilha: último a entrar, primeiro a sair.""",
    parameters={
        "name": {
            "type": "string",
            "description": "Nome/descrição para identificar este stash"
        },
        "include_untracked": {
            "type": "boolean",
            "description": "Se True, inclui arquivos novos não rastreados",
            "default": True
        }
    },
    required=["name"],
    complexity="simple"
)
def git_stash_save(name: str, workspace: Path, include_untracked: bool = True) -> str:
    """Salva mudanças em stash."""
    
    if not _is_git_repo(workspace):
        return "❌ Workspace não é um repositório Git."
    
    if not _has_changes(workspace):
        return "ℹ️ Nenhuma mudança para salvar em stash."
    
    untracked = "-u" if include_untracked else ""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"[STASH] {name} ({timestamp})"
    
    success, stdout, stderr = _run_git(f'stash push {untracked} -m "{message}"', workspace)
    
    if not success:
        return f"❌ Erro ao criar stash: {stderr}"
    
    # Lista stashes para mostrar posição
    success, stash_list, _ = _run_git("stash list --oneline", workspace)
    stash_count = len(stash_list.splitlines()) if stash_list else 0
    
    return (
        f"✅ Mudanças salvas em stash!\n\n"
        f"💾 Nome: {name}\n"
        f"📍 Posição: stash@{{0}} (mais recente)\n"
        f"📚 Total de stashes: {stash_count}\n\n"
        f"💡 Para restaurar: git_stash_apply() ou git_stash_apply(\"stash@{{0}}\")"
    )


@tool(
    description="""📤 Restaura mudanças de um STASH.

Por padrão restaura o stash mais recente (stash@{0}).
Pode especificar um stash específico pelo índice ou nome.""",
    parameters={
        "stash_ref": {
            "type": "string",
            "description": "Referência do stash (ex: 'stash@{0}', 'stash@{1}'). Se vazio, usa o mais recente.",
            "default": "stash@{0}"
        },
        "drop": {
            "type": "boolean",
            "description": "Se True, remove o stash após aplicar (pop). Se False, mantém o stash (apply).",
            "default": True
        }
    },
    required=[],
    complexity="simple"
)
def git_stash_apply(workspace: Path, stash_ref: str = "stash@{0}", drop: bool = True) -> str:
    """Restaura mudanças de um stash."""
    
    if not _is_git_repo(workspace):
        return "❌ Workspace não é um repositório Git."
    
    # Verifica se há stashes
    success, stash_list, _ = _run_git("stash list", workspace)
    if not stash_list:
        return "ℹ️ Nenhum stash disponível para restaurar."
    
    # Aplica ou faz pop do stash
    action = "pop" if drop else "apply"
    success, stdout, stderr = _run_git(f"stash {action} {stash_ref}", workspace)
    
    if not success:
        return f"❌ Erro ao restaurar stash: {stderr}"
    
    action_desc = "restaurado e removido" if drop else "restaurado (mantido na lista)"
    
    return (
        f"✅ Stash {action_desc}!\n\n"
        f"📤 Stash: {stash_ref}\n"
        f"📝 Mudanças aplicadas ao working directory\n\n"
        f"💡 Use git_status() para ver os arquivos restaurados"
    )


@tool(
    description="""📋 Lista todos os stashes salvos.""",
    parameters={},
    required=[],
    complexity="simple"
)
def git_stash_list(workspace: Path) -> str:
    """Lista stashes disponíveis."""
    
    if not _is_git_repo(workspace):
        return "❌ Workspace não é um repositório Git."
    
    success, stash_list, stderr = _run_git("stash list", workspace)
    
    if not stash_list:
        return "📋 Nenhum stash salvo.\n\n💡 Use git_stash_save('nome') para salvar mudanças."
    
    lines = stash_list.splitlines()
    formatted = []
    for line in lines:
        # Format: stash@{0}: On branch: message
        parts = line.split(": ", 2)
        if len(parts) >= 3:
            ref = parts[0]
            branch = parts[1].replace("On ", "📍 ")
            message = parts[2]
            formatted.append(f"  💾 {ref}\n     {branch}\n     📝 {message}\n")
        else:
            formatted.append(f"  💾 {line}\n")
    
    return (
        f"📋 Stashes salvos ({len(lines)}):\n\n" +
        "\n".join(formatted) +
        f"\n💡 Para restaurar: git_stash_apply(\"stash@{{N}}\")"
    )


# ============================================================================
# BRANCH MANAGEMENT
# ============================================================================

@tool(
    description="""🌿 Cria uma nova BRANCH para trabalho isolado.

Use para:
- Experimentar mudanças sem afetar a branch principal
- Desenvolver features em paralelo
- Criar backup do estado atual antes de mudanças grandes""",
    parameters={
        "name": {
            "type": "string",
            "description": "Nome da branch (ex: 'feature-auth', 'experiment-refactor')"
        },
        "checkout": {
            "type": "boolean",
            "description": "Se True, muda para a nova branch após criar",
            "default": True
        }
    },
    required=["name"],
    complexity="simple"
)
def git_branch_create(name: str, workspace: Path, checkout: bool = True) -> str:
    """Cria nova branch."""
    
    if not _is_git_repo(workspace):
        return "❌ Workspace não é um repositório Git."
    
    # Verifica se branch já existe
    success, branches, _ = _run_git("branch --list", workspace)
    if name in [b.strip().lstrip('* ') for b in branches.splitlines()]:
        return f"❌ Branch '{name}' já existe. Use git_branch_switch('{name}') para mudar para ela."
    
    current_branch = _get_current_branch(workspace)
    
    if checkout:
        success, _, stderr = _run_git(f"checkout -b {name}", workspace)
    else:
        success, _, stderr = _run_git(f"branch {name}", workspace)
    
    if not success:
        return f"❌ Erro ao criar branch: {stderr}"
    
    action = "criada e ativada" if checkout else "criada"
    
    return (
        f"✅ Branch '{name}' {action}!\n\n"
        f"🌿 Branch anterior: {current_branch}\n"
        f"🌿 Branch atual: {name if checkout else current_branch}\n\n"
        f"💡 Para voltar: git_branch_switch('{current_branch}')"
    )


@tool(
    description="""🔀 Muda para outra BRANCH existente.""",
    parameters={
        "name": {
            "type": "string",
            "description": "Nome da branch para mudar"
        },
        "create_if_missing": {
            "type": "boolean",
            "description": "Se True, cria a branch se não existir",
            "default": False
        }
    },
    required=["name"],
    complexity="simple"
)
def git_branch_switch(name: str, workspace: Path, create_if_missing: bool = False) -> str:
    """Muda para outra branch."""
    
    if not _is_git_repo(workspace):
        return "❌ Workspace não é um repositório Git."
    
    # Verifica mudanças não commitadas
    if _has_changes(workspace):
        return (
            f"⚠️ Existem mudanças não commitadas!\n\n"
            f"Opções:\n"
            f"  1. git_checkpoint('mensagem') - Salvar como commit\n"
            f"  2. git_stash_save('nome') - Guardar temporariamente\n"
            f"  3. git_rollback('HEAD', hard=True) - Descartar mudanças\n"
        )
    
    current_branch = _get_current_branch(workspace)
    
    flag = "-b" if create_if_missing else ""
    success, _, stderr = _run_git(f"checkout {flag} {name}", workspace)
    
    if not success:
        return f"❌ Erro ao mudar de branch: {stderr}"
    
    return (
        f"✅ Mudou para branch '{name}'!\n\n"
        f"🌿 Branch anterior: {current_branch}\n"
        f"🌿 Branch atual: {name}"
    )


@tool(
    description="""📋 Lista todas as BRANCHES do repositório.""",
    parameters={
        "show_remote": {
            "type": "boolean",
            "description": "Se True, mostra também branches remotas",
            "default": False
        }
    },
    required=[],
    complexity="simple"
)
def git_branch_list(workspace: Path, show_remote: bool = False) -> str:
    """Lista branches."""
    
    if not _is_git_repo(workspace):
        return "❌ Workspace não é um repositório Git."
    
    flag = "-a" if show_remote else ""
    success, branches, _ = _run_git(f"branch {flag} -v", workspace)
    
    if not success or not branches:
        return "📋 Nenhuma branch encontrada."
    
    lines = branches.splitlines()
    formatted = []
    for line in lines:
        if line.startswith('*'):
            formatted.append(f"  👉 {line[2:]} (atual)")
        else:
            formatted.append(f"  🌿 {line.strip()}")
    
    return (
        f"📋 Branches ({len(lines)}):\n\n" +
        "\n".join(formatted)
    )


# ============================================================================
# STATUS AND HISTORY
# ============================================================================

@tool(
    description="""📊 Mostra o STATUS atual do repositório Git.

Exibe:
- Branch atual
- Arquivos modificados, novos, deletados
- Estado do staging area
- Resumo das mudanças""",
    parameters={},
    required=[],
    complexity="simple"
)
def git_status(workspace: Path) -> str:
    """Mostra status do repositório usando Rich para formatação."""
    
    if not _is_git_repo(workspace):
        return "❌ Workspace não é um repositório Git. Use git_init() para inicializar."
    
    branch = _get_current_branch(workspace)
    
    # Status porcelain para parsing
    success, status, _ = _run_git("status --porcelain", workspace)
    
    if not status:
        panel = Panel(
            f"📍 Branch: [green]{branch}[/green]\n📝 Nenhuma mudança pendente",
            title="✅ Working directory limpo",
            border_style="green"
        )
        return _render_to_string(panel)
    
    lines = status.splitlines()
    
    # Conta tipos de mudanças
    staged = sum(1 for l in lines if l[0] != ' ' and l[0] != '?')
    modified = sum(1 for l in lines if 'M' in l[:2])
    untracked = sum(1 for l in lines if l.startswith('??'))
    deleted = sum(1 for l in lines if 'D' in l[:2])
    
    # Tabela de resumo
    summary_table = Table(
        title=f"📊 Status do Repositório",
        box=box.ROUNDED,
        show_header=False,
        border_style="cyan"
    )
    summary_table.add_column("Info", style="bold")
    summary_table.add_column("Valor")
    summary_table.add_row("📍 Branch", f"[green]{branch}[/green]")
    summary_table.add_row("✏️  Modificados", f"[yellow]{modified}[/yellow]")
    summary_table.add_row("🆕 Não rastreados", f"[red]{untracked}[/red]")
    summary_table.add_row("🗑️  Deletados", f"[red]{deleted}[/red]")
    summary_table.add_row("📦 Staged", f"[green]{staged}[/green]")
    
    # Tabela de arquivos
    files_table = Table(
        title="📂 Arquivos",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold"
    )
    files_table.add_column("Status", width=22)
    files_table.add_column("Arquivo")
    
    for line in lines[:15]:
        status_code = line[:2]
        filename = line[3:]
        
        if status_code == '??':
            files_table.add_row("[red]❓ não rastreado[/red]", filename)
        elif 'M' in status_code:
            staged_marker = "(staged)" if status_code[0] == 'M' else ""
            files_table.add_row(f"[yellow]✏️  modificado {staged_marker}[/yellow]", filename)
        elif 'D' in status_code:
            files_table.add_row("[red]🗑️  deletado[/red]", filename)
        elif 'A' in status_code:
            files_table.add_row("[green]🆕 novo (staged)[/green]", filename)
        else:
            files_table.add_row(f"[dim]{status_code}[/dim]", filename)
    
    if len(lines) > 15:
        files_table.add_row("...", f"[dim]e mais {len(lines) - 15} arquivos[/dim]")
    
    # Dicas
    tips = Panel(
        "[cyan]git_checkpoint('mensagem')[/cyan] - Salvar estado atual\n"
        "[cyan]git_rollback('HEAD')[/cyan] - Desfazer mudanças",
        title="💡 Próximos passos",
        border_style="blue"
    )
    
    return (
        _render_to_string(summary_table) +
        _render_to_string(files_table) +
        _render_to_string(tips)
    )


@tool(
    description="""📜 Mostra o HISTÓRICO de commits (checkpoints).

Útil para:
- Ver checkpoints disponíveis
- Encontrar hash para rollback
- Revisar o que foi feito na sessão""",
    parameters={
        "limit": {
            "type": "integer",
            "description": "Número máximo de commits a mostrar",
            "default": 10
        },
        "oneline": {
            "type": "boolean",
            "description": "Se True, mostra formato compacto (uma linha por commit)",
            "default": True
        }
    },
    required=[],
    complexity="simple"
)
def git_history(workspace: Path, limit: int = 10, oneline: bool = True) -> str:
    """Mostra histórico de commits usando Rich para formatação."""
    
    if not _is_git_repo(workspace):
        return "❌ Workspace não é um repositório Git."
    
    if oneline:
        format_str = "--oneline"
    else:
        format_str = '--format="%h | %s | %cr | %an"'
    
    success, log, _ = _run_git(f"log {format_str} -n {limit}", workspace)
    
    if not success or not log:
        return "📜 Nenhum commit no histórico."
    
    lines = log.splitlines()
    
    # Cria tabela de histórico
    history_table = Table(
        title=f"📜 Histórico de Commits (últimos {limit})",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="cyan"
    )
    history_table.add_column("Hash", style="cyan", width=8)
    history_table.add_column("Tipo", width=4)
    history_table.add_column("Mensagem")
    
    for line in lines:
        parts = line.split(" ", 1)
        hash_val = parts[0]
        msg = parts[1] if len(parts) > 1 else ""
        
        # Identifica tipo
        if "[CHECKPOINT]" in msg:
            icon = "🔖"
            style = "yellow"
        elif "🎉" in msg or "inicial" in msg.lower():
            icon = "🎉"
            style = "green"
        else:
            icon = "📝"
            style = "white"
        
        # Trunca mensagem se muito longa
        msg_display = msg[:55] + "..." if len(msg) > 55 else msg
        history_table.add_row(hash_val, icon, f"[{style}]{msg_display}[/{style}]")
    
    # Dicas
    tips = Panel(
        "[cyan]git_rollback('HASH')[/cyan] - Reverter para commit\n"
        f"[cyan]git_history(limit={limit + 10})[/cyan] - Ver mais commits",
        title="💡 Dicas",
        border_style="blue"
    )
    
    return _render_to_string(history_table) + _render_to_string(tips)


# ============================================================================
# REVIEW DASHBOARD (Ferramenta de Revisão Final)
# ============================================================================

@tool(
    description="""🎯 DASHBOARD DE REVISÃO - Mostra visão completa do estado Git com comandos de ação.

Use esta ferramenta ao FINAL de uma sessão de trabalho para:
- Ver resumo de todas as mudanças
- Listar checkpoints criados
- Obter comandos prontos para rollback ou commit

Esta é a ferramenta de "revisão final" que mostra tudo em um painel visual.""",
    parameters={
        "session_commits": {
            "type": "integer",
            "description": "Número de commits recentes a considerar como 'desta sessão'",
            "default": 5
        }
    },
    required=[],
    complexity="simple"
)
def git_review(workspace: Path, session_commits: int = 5) -> str:
    """Dashboard de revisão final usando Rich para formatação."""
    
    if not _is_git_repo(workspace):
        panel = Panel(
            "💡 Use [cyan]git_init()[/cyan] para inicializar o versionamento.",
            title="❌ Workspace não é um repositório Git",
            border_style="red"
        )
        return _render_to_string(panel)
    
    # Coleta informações
    branch = _get_current_branch(workspace)
    
    # Status atual
    _, status_output, _ = _run_git("status --porcelain", workspace)
    status_lines = status_output.splitlines() if status_output else []
    
    # Histórico recente
    _, history, _ = _run_git(f"log --oneline -n {session_commits}", workspace)
    history_lines = history.splitlines() if history else []
    
    # Stashes
    _, stashes, _ = _run_git("stash list --oneline", workspace)
    stash_lines = stashes.splitlines() if stashes else []
    
    # Primeiro commit da sessão (para referência de rollback total)
    first_commit_hash = history_lines[-1].split()[0] if history_lines else "HEAD"
    
    # =========================================================================
    # TABELA: Status Geral
    # =========================================================================
    status_table = Table(
        title=f"📊 GIT REVIEW - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        box=box.ROUNDED,
        show_header=False,
        title_style="bold cyan",
        border_style="cyan"
    )
    status_table.add_column("Info", style="bold")
    status_table.add_column("Valor")
    status_table.add_row("📍 Branch", f"[green]{branch}[/green]")
    status_table.add_row("📁 Arquivos modificados", f"[yellow]{len(status_lines)}[/yellow]")
    status_table.add_row("🔖 Checkpoints recentes", f"[blue]{len(history_lines)}[/blue]")
    status_table.add_row("💾 Stashes salvos", f"[magenta]{len(stash_lines)}[/magenta]")
    
    # =========================================================================
    # TABELA: Arquivos Modificados
    # =========================================================================
    files_table = Table(
        title="📁 Arquivos Modificados",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold yellow"
    )
    files_table.add_column("Status", width=20)
    files_table.add_column("Arquivo", style="white")
    
    if status_lines:
        for line in status_lines[:10]:
            formatted = _format_file_status(line)
            # Parse formatted string
            if "modificado" in formatted:
                files_table.add_row("[yellow]✏️  modificado[/yellow]", line[3:])
            elif "não rastreado" in formatted:
                files_table.add_row("[red]❓ não rastreado[/red]", line[3:])
            elif "deletado" in formatted:
                files_table.add_row("[red]🗑️  deletado[/red]", line[3:])
            elif "novo" in formatted:
                files_table.add_row("[green]🆕 novo[/green]", line[3:])
            else:
                files_table.add_row(line[:2], line[3:])
        if len(status_lines) > 10:
            files_table.add_row("...", f"[dim]e mais {len(status_lines) - 10} arquivos[/dim]")
    else:
        files_table.add_row("[green]✅[/green]", "[green]Working directory limpo[/green]")
    
    # =========================================================================
    # TABELA: Histórico de Checkpoints
    # =========================================================================
    history_table = Table(
        title="🔖 Checkpoints Recentes",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold blue"
    )
    history_table.add_column("Hash", style="cyan", width=8)
    history_table.add_column("Mensagem")
    
    if history_lines:
        for line in history_lines:
            parts = line.split(" ", 1)
            hash_val = parts[0]
            msg = parts[1] if len(parts) > 1 else ""
            icon = "🔖" if "[CHECKPOINT]" in msg else "📝"
            # Trunca mensagem se muito longa
            msg_display = msg[:50] + "..." if len(msg) > 50 else msg
            history_table.add_row(f"[cyan]{hash_val}[/cyan]", f"{icon} {msg_display}")
    else:
        history_table.add_row("-", "[dim]Nenhum commit encontrado[/dim]")
    
    # =========================================================================
    # TABELA: Stashes (se houver)
    # =========================================================================
    stash_table = None
    if stash_lines:
        stash_table = Table(
            title="💾 Stashes Salvos",
            box=box.SIMPLE,
            show_header=True,
            header_style="bold magenta"
        )
        stash_table.add_column("Ref", style="magenta", width=12)
        stash_table.add_column("Descrição")
        
        for line in stash_lines[:5]:
            parts = line.split(": ", 1)
            ref = parts[0] if parts else line
            desc = parts[1] if len(parts) > 1 else ""
            stash_table.add_row(ref, desc[:50])
    
    # =========================================================================
    # TABELA: Comandos Disponíveis
    # =========================================================================
    cmd_table = Table(
        title="🔧 Comandos Disponíveis",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold green",
        border_style="green"
    )
    cmd_table.add_column("Ação", style="bold", width=25)
    cmd_table.add_column("Comando")
    
    if status_lines:
        cmd_table.add_row("📦 Salvar mudanças", '[cyan]git_checkpoint("mensagem")[/cyan]')
        cmd_table.add_row("⏪ Descartar mudanças", '[yellow]git_rollback("HEAD", hard=True)[/yellow]')
    
    if history_lines and len(history_lines) > 1:
        cmd_table.add_row("⏪ Rollback p/ início", f'[yellow]git_rollback("{first_commit_hash}~1")[/yellow]')
    
    cmd_table.add_row("💾 Guardar para depois", '[cyan]git_stash_save("nome")[/cyan]')
    cmd_table.add_row("🌿 Criar branch backup", f'[cyan]git_branch_create("backup-{datetime.now().strftime("%Y%m%d")}")[/cyan]')
    
    # =========================================================================
    # TABELA: Comandos Git Nativos
    # =========================================================================
    native_table = Table(
        title="📋 Comandos Git Nativos (copiar/colar)",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold white"
    )
    native_table.add_column("Descrição", style="dim", width=30)
    native_table.add_column("Comando", style="white")
    
    native_table.add_row("Commit definitivo", 'git add -A && git commit -m "feat: msg"')
    native_table.add_row("Rollback total", f'git reset --hard {first_commit_hash}~1')
    native_table.add_row("Ver diferenças", 'git diff')
    native_table.add_row("Criar branch backup", f'git branch backup-{datetime.now().strftime("%Y%m%d")}')
    
    # =========================================================================
    # RENDERIZA TUDO
    # =========================================================================
    output_parts = []
    output_parts.append(_render_to_string(status_table))
    output_parts.append(_render_to_string(files_table))
    output_parts.append(_render_to_string(history_table))
    if stash_table:
        output_parts.append(_render_to_string(stash_table))
    output_parts.append(_render_to_string(cmd_table))
    output_parts.append(_render_to_string(native_table))
    
    return "\n".join(output_parts)


# ============================================================================
# SESSION MANAGEMENT (Branch-based workflow)
# ============================================================================

@tool(
    description="""🚀 INICIA UMA SESSÃO DE TRABALHO criando um branch isolado.

Esta ferramenta DEVE ser chamada no INÍCIO de cada sessão de trabalho.
Cria um branch com nome automático baseado na data/hora ou descrição fornecida.

Benefícios:
- Master/main fica protegido
- Todos os commits da sessão ficam isolados
- Fácil reverter ou descartar toda a sessão
- No final, pode fazer merge ou squash""",
    parameters={
        "description": {
            "type": "string",
            "description": "Descrição curta da tarefa (ex: 'criar-api-fastapi', 'refatorar-auth'). Será usada no nome do branch."
        },
        "base_branch": {
            "type": "string",
            "description": "Branch base para criar o novo branch (padrão: branch atual)",
            "default": ""
        }
    },
    required=["description"],
    complexity="simple"
)
def git_session_start(description: str, workspace: Path, base_branch: str = "") -> str:
    """Inicia uma sessão de trabalho criando um branch isolado."""
    
    # Inicializa Git se necessário
    if not _is_git_repo(workspace):
        _run_git("init", workspace)
        _run_git("add -A", workspace)
        _run_git('commit -m "🎉 Commit inicial"', workspace)
    
    # Verifica se há mudanças não commitadas
    if _has_changes(workspace):
        return (
            "⚠️ Existem mudanças não commitadas!\n\n"
            "Antes de iniciar uma nova sessão, você precisa:\n"
            "  1. git_checkpoint('mensagem') - Salvar mudanças\n"
            "  2. git_stash_save('nome') - Guardar temporariamente\n"
            "  3. git_rollback('HEAD', hard=True) - Descartar mudanças"
        )
    
    # Gera nome do branch
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    # Sanitiza descrição para nome de branch
    safe_desc = description.lower().replace(" ", "-").replace("_", "-")
    safe_desc = "".join(c for c in safe_desc if c.isalnum() or c == "-")[:30]
    branch_name = f"session/{timestamp}-{safe_desc}"
    
    # Guarda branch atual
    current_branch = _get_current_branch(workspace)
    
    # Se especificou base_branch, vai para ela primeiro
    if base_branch and base_branch != current_branch:
        success, _, stderr = _run_git(f"checkout {base_branch}", workspace)
        if not success:
            return f"❌ Erro ao mudar para branch base '{base_branch}': {stderr}"
    
    # Cria e muda para o novo branch
    success, _, stderr = _run_git(f"checkout -b {branch_name}", workspace)
    if not success:
        return f"❌ Erro ao criar branch: {stderr}"
    
    # Painel de sucesso usando Rich
    info_table = Table(show_header=False, box=box.SIMPLE)
    info_table.add_column("Item", style="bold")
    info_table.add_column("Valor")
    info_table.add_row("🌿 Branch criado", f"[green]{branch_name}[/green]")
    info_table.add_row("📍 Branch base", f"[cyan]{base_branch or current_branch}[/cyan]")
    info_table.add_row("📝 Descrição", description)
    info_table.add_row("⏰ Iniciado em", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    panel = Panel(
        info_table,
        title="🚀 Sessão de Trabalho Iniciada",
        border_style="green",
        box=box.ROUNDED
    )
    
    output = _render_to_string(panel)
    output += "\n💡 Dicas:\n"
    output += "  • Seus commits ficarão isolados neste branch\n"
    output += "  • Use checkpoint= nas ferramentas para salvar progresso\n"
    output += f"  • No final, use git_session_end() para revisar e decidir\n"
    output += f"  • Para voltar ao master: git_branch_switch('{base_branch or current_branch}')\n"
    
    return output


@tool(
    description="""🏁 FINALIZA A SESSÃO DE TRABALHO com review completo e opções de merge.

Esta ferramenta DEVE ser chamada no FINAL de cada sessão de trabalho.
Mostra:
- Resumo de todos os commits da sessão
- Arquivos modificados
- Opções de merge (squash, merge, ou descartar)
- Comandos prontos para executar""",
    parameters={
        "target_branch": {
            "type": "string",
            "description": "Branch para fazer merge (padrão: master ou main)",
            "default": "master"
        }
    },
    required=[],
    complexity="simple"
)
def git_session_end(workspace: Path, target_branch: str = "master") -> str:
    """Finaliza sessão de trabalho com review e opções de merge."""
    
    if not _is_git_repo(workspace):
        return "❌ Workspace não é um repositório Git."
    
    current_branch = _get_current_branch(workspace)
    
    # Verifica se está em um branch de sessão
    is_session_branch = current_branch.startswith("session/")
    
    # Verifica mudanças não commitadas
    has_uncommitted = _has_changes(workspace)
    
    # Conta commits à frente do target
    success, ahead_count, _ = _run_git(
        f"rev-list --count {target_branch}..{current_branch}", 
        workspace, 
        check=False
    )
    commits_ahead = int(ahead_count) if success and ahead_count.isdigit() else 0
    
    # Lista commits da sessão
    _, commits_log, _ = _run_git(
        f"log {target_branch}..{current_branch} --oneline",
        workspace,
        check=False
    )
    commits_list = commits_log.splitlines() if commits_log else []
    
    # Lista arquivos modificados
    _, files_changed, _ = _run_git(
        f"diff --name-only {target_branch}..{current_branch}",
        workspace,
        check=False
    )
    files_list = files_changed.splitlines() if files_changed else []
    
    # =========================================================================
    # TABELA: Resumo da Sessão
    # =========================================================================
    summary_table = Table(
        title="🏁 Resumo da Sessão de Trabalho",
        box=box.ROUNDED,
        show_header=False,
        border_style="cyan"
    )
    summary_table.add_column("Item", style="bold")
    summary_table.add_column("Valor")
    
    summary_table.add_row("🌿 Branch atual", f"[green]{current_branch}[/green]")
    summary_table.add_row("🎯 Branch destino", f"[cyan]{target_branch}[/cyan]")
    summary_table.add_row("📊 Commits na sessão", f"[yellow]{commits_ahead}[/yellow]")
    summary_table.add_row("📁 Arquivos alterados", f"[yellow]{len(files_list)}[/yellow]")
    
    if has_uncommitted:
        summary_table.add_row("⚠️ Mudanças pendentes", "[red]SIM - commit necessário![/red]")
    else:
        summary_table.add_row("✅ Working directory", "[green]Limpo[/green]")
    
    # =========================================================================
    # TABELA: Commits da Sessão
    # =========================================================================
    commits_table = Table(
        title="🔖 Commits da Sessão",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold blue"
    )
    commits_table.add_column("Hash", style="cyan", width=8)
    commits_table.add_column("Mensagem")
    
    if commits_list:
        for line in commits_list[:15]:
            parts = line.split(" ", 1)
            hash_val = parts[0]
            msg = parts[1] if len(parts) > 1 else ""
            icon = "🔖" if "[CHECKPOINT]" in msg else "📝"
            msg_display = msg[:55] + "..." if len(msg) > 55 else msg
            commits_table.add_row(hash_val, f"{icon} {msg_display}")
        if len(commits_list) > 15:
            commits_table.add_row("...", f"[dim]e mais {len(commits_list) - 15} commits[/dim]")
    else:
        commits_table.add_row("-", "[dim]Nenhum commit na sessão[/dim]")
    
    # =========================================================================
    # TABELA: Arquivos Alterados
    # =========================================================================
    files_table = Table(
        title="📁 Arquivos Alterados",
        box=box.SIMPLE,
        show_header=False
    )
    files_table.add_column("Arquivo")
    
    if files_list:
        for f in files_list[:10]:
            files_table.add_row(f"  📄 {f}")
        if len(files_list) > 10:
            files_table.add_row(f"  [dim]... e mais {len(files_list) - 10} arquivos[/dim]")
    else:
        files_table.add_row("  [dim]Nenhum arquivo alterado[/dim]")
    
    # =========================================================================
    # TABELA: Opções de Finalização
    # =========================================================================
    options_table = Table(
        title="🔧 Opções de Finalização",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold green",
        border_style="green"
    )
    options_table.add_column("Opção", style="bold", width=20)
    options_table.add_column("Comando / Ação")
    options_table.add_column("Resultado")
    
    if has_uncommitted:
        options_table.add_row(
            "📦 Salvar pendentes",
            '[cyan]git_checkpoint("msg")[/cyan]',
            "Commit das mudanças"
        )
    
    options_table.add_row(
        "🔀 Merge direto",
        f'[yellow]git checkout {target_branch} && git merge {current_branch}[/yellow]',
        "Mantém todos os commits"
    )
    
    options_table.add_row(
        "📦 Squash (1 commit)",
        f'[yellow]git checkout {target_branch} && git merge --squash {current_branch}[/yellow]',
        "Junta tudo em 1 commit"
    )
    
    options_table.add_row(
        "🗑️ Descartar sessão",
        f'[red]git checkout {target_branch} && git branch -D {current_branch}[/red]',
        "Remove branch e mudanças"
    )
    
    options_table.add_row(
        "💾 Manter para depois",
        '[dim]Não fazer nada[/dim]',
        "Branch continua disponível"
    )
    
    # =========================================================================
    # RENDERIZA TUDO
    # =========================================================================
    output_parts = []
    output_parts.append(_render_to_string(summary_table))
    output_parts.append(_render_to_string(commits_table))
    output_parts.append(_render_to_string(files_table))
    output_parts.append(_render_to_string(options_table))
    
    # Comandos prontos para copiar
    output_parts.append("\n📋 Comandos Git prontos para copiar:\n")
    output_parts.append(f"# Merge direto (mantém histórico):\n")
    output_parts.append(f"git checkout {target_branch} && git merge {current_branch}\n\n")
    output_parts.append(f"# Squash (1 commit limpo):\n")
    output_parts.append(f"git checkout {target_branch} && git merge --squash {current_branch} && git commit -m \"feat: descrição\"\n\n")
    output_parts.append(f"# Descartar sessão:\n")
    output_parts.append(f"git checkout {target_branch} && git branch -D {current_branch}\n")
    
    return "\n".join(output_parts)


# ============================================================================
# HELPER FUNCTION FOR CHECKPOINT PARAMETER
# ============================================================================

def create_checkpoint_if_requested(
    workspace: Path, 
    checkpoint: Optional[str], 
    operation: str,
    filepath: str
) -> Optional[str]:
    """
    Cria um checkpoint se solicitado.
    
    Esta função é usada pelas outras ferramentas (write_file, edit_lines, etc.)
    para criar checkpoints automáticos.
    
    Args:
        workspace: Path do workspace
        checkpoint: Mensagem do checkpoint ou None/False para não criar
        operation: Descrição da operação (ex: "write_file", "edit_lines")
        filepath: Arquivo sendo modificado
        
    Returns:
        Mensagem de sucesso/erro ou None se checkpoint não foi solicitado
    """
    if not checkpoint:
        return None
    
    if not _is_git_repo(workspace):
        return None  # Silenciosamente ignora se não é repo git
    
    # Gera mensagem automática se checkpoint=True (ou string vazia)
    if checkpoint is True or checkpoint == "":
        message = f"auto-checkpoint: {operation} {filepath}"
    else:
        message = str(checkpoint)
    
    # Adiciona e commita
    _run_git("add -A", workspace)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_message = f"🔖 [CHECKPOINT] {message} ({timestamp})"
    
    success, _, stderr = _run_git(f'commit -m "{commit_message}"', workspace)
    
    if success:
        _, commit_hash, _ = _run_git("rev-parse --short HEAD", workspace)
        return f"🔖 Checkpoint criado: {commit_hash}"
    
    return None

