"""
Git version control tools for the Modern AI Agent.

Provides checkpoint, rollback, stash, and branch management for safe code editing.
"""
import subprocess
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from .tool_decorator import tool

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
    """Mostra status do repositório."""
    
    if not _is_git_repo(workspace):
        return "❌ Workspace não é um repositório Git. Use git_init() para inicializar."
    
    branch = _get_current_branch(workspace)
    
    # Status porcelain para parsing
    success, status, _ = _run_git("status --porcelain", workspace)
    
    if not status:
        return (
            f"✅ Working directory está limpo!\n\n"
            f"📍 Branch: {branch}\n"
            f"📝 Nenhuma mudança pendente"
        )
    
    lines = status.splitlines()
    formatted_files = [_format_file_status(line) for line in lines]
    
    # Conta tipos de mudanças
    staged = sum(1 for l in lines if l[0] != ' ' and l[0] != '?')
    modified = sum(1 for l in lines if 'M' in l[:2])
    untracked = sum(1 for l in lines if l.startswith('??'))
    deleted = sum(1 for l in lines if 'D' in l[:2])
    
    return (
        f"📊 Status do Repositório\n"
        f"{'=' * 40}\n\n"
        f"📍 Branch: {branch}\n\n"
        f"📈 Resumo:\n"
        f"  ✏️  Modificados: {modified}\n"
        f"  🆕 Não rastreados: {untracked}\n"
        f"  🗑️  Deletados: {deleted}\n"
        f"  📦 Staged: {staged}\n\n"
        f"📂 Arquivos:\n" +
        "\n".join(formatted_files) +
        f"\n\n💡 Próximos passos:\n"
        f"  - git_checkpoint('mensagem') - Salvar estado atual\n"
        f"  - git_rollback('HEAD') - Desfazer mudanças"
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
    """Mostra histórico de commits."""
    
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
    formatted = []
    for i, line in enumerate(lines):
        # Identifica checkpoints
        if "[CHECKPOINT]" in line:
            formatted.append(f"  🔖 {line}")
        elif "🎉" in line or "inicial" in line.lower():
            formatted.append(f"  🎉 {line}")
        else:
            formatted.append(f"  📝 {line}")
    
    return (
        f"📜 Histórico de Commits (últimos {limit})\n"
        f"{'=' * 40}\n\n" +
        "\n".join(formatted) +
        f"\n\n💡 Para rollback: git_rollback('HASH')\n"
        f"💡 Para ver mais: git_history(limit=20)"
    )


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
    """Dashboard de revisão final."""
    
    if not _is_git_repo(workspace):
        return (
            "❌ Workspace não é um repositório Git.\n\n"
            "💡 Use git_init() para inicializar o versionamento."
        )
    
    # Coleta informações
    branch = _get_current_branch(workspace)
    
    # Status atual
    _, status_output, _ = _run_git("status --porcelain", workspace)
    status_lines = status_output.splitlines() if status_output else []
    
    # Diff stat
    _, diff_stat, _ = _run_git("diff --stat", workspace)
    
    # Histórico recente
    _, history, _ = _run_git(f"log --oneline -n {session_commits}", workspace)
    history_lines = history.splitlines() if history else []
    
    # Stashes
    _, stashes, _ = _run_git("stash list --oneline", workspace)
    stash_lines = stashes.splitlines() if stashes else []
    
    # Primeiro commit da sessão (para referência de rollback total)
    first_commit_hash = history_lines[-1].split()[0] if history_lines else "HEAD"
    
    # Monta o dashboard
    separator = "═" * 60
    section_sep = "─" * 60
    
    # Seção: Header
    output = f"""
╔{separator}╗
║  📊 GIT REVIEW - Dashboard de Revisão                        ║
║  📅 {datetime.now().strftime("%Y-%m-%d %H:%M")}                                           ║
╠{separator}╣
"""
    
    # Seção: Status Geral
    output += f"""║  📍 BRANCH ATUAL: {branch:<41} ║
╠{separator}╣
"""
    
    # Seção: Arquivos Modificados
    if status_lines:
        output += f"║  📁 ARQUIVOS MODIFICADOS ({len(status_lines)}):                           ║\n"
        for line in status_lines[:10]:
            formatted = _format_file_status(line)
            output += f"║  {formatted:<56} ║\n"
        if len(status_lines) > 10:
            output += f"║  ... e mais {len(status_lines) - 10} arquivos                              ║\n"
    else:
        output += f"║  ✅ Nenhuma mudança pendente (working directory limpo)     ║\n"
    
    output += f"╠{section_sep}╣\n"
    
    # Seção: Checkpoints da Sessão
    output += f"║  🔖 CHECKPOINTS RECENTES ({len(history_lines)}):                            ║\n"
    if history_lines:
        for line in history_lines:
            # Trunca se muito longo
            display = line[:52] + "..." if len(line) > 55 else line
            icon = "🔖" if "[CHECKPOINT]" in line else "📝"
            output += f"║    {icon} {display:<53} ║\n"
    else:
        output += f"║    (nenhum commit encontrado)                            ║\n"
    
    output += f"╠{section_sep}╣\n"
    
    # Seção: Stashes
    if stash_lines:
        output += f"║  💾 STASHES SALVOS ({len(stash_lines)}):                                  ║\n"
        for line in stash_lines[:3]:
            display = line[:52] + "..." if len(line) > 55 else line
            output += f"║    💾 {display:<53} ║\n"
    
    output += f"╠{section_sep}╣\n"
    
    # Seção: Comandos de Ação
    output += f"""║  🔧 COMANDOS DISPONÍVEIS:                                    ║
╠{section_sep}╣
"""
    
    if status_lines:
        output += f"""║  📦 SALVAR MUDANÇAS:                                         ║
║    git_checkpoint("descrição das mudanças")                ║
║                                                             ║
║  ⏪ DESCARTAR MUDANÇAS LOCAIS:                               ║
║    git_rollback("HEAD", hard=True)                         ║
║                                                             ║
"""
    
    if history_lines and len(history_lines) > 1:
        output += f"""║  ⏪ ROLLBACK PARA INÍCIO DA SESSÃO:                           ║
║    git_rollback("{first_commit_hash}~1")                             ║
║                                                             ║
"""
    
    output += f"""║  💾 GUARDAR PARA DEPOIS:                                     ║
║    git_stash_save("trabalho em andamento")                 ║
║                                                             ║
║  🌿 CRIAR BRANCH DE BACKUP:                                  ║
║    git_branch_create("backup-{datetime.now().strftime('%Y%m%d')}")                      ║
╠{section_sep}╣
"""
    
    # Seção: Comandos Git Nativos (para copiar)
    output += f"""║  📋 COMANDOS GIT NATIVOS (copiar/colar):                     ║
╠{section_sep}╣
║  # Commit definitivo                                        ║
║  git add -A && git commit -m "feat: descrição"             ║
║                                                             ║
║  # Rollback total para início da sessão                     ║
║  git reset --hard {first_commit_hash}~1                              ║
║                                                             ║
║  # Ver diferenças detalhadas                                ║
║  git diff                                                   ║
║                                                             ║
║  # Criar branch de backup                                   ║
║  git branch backup-session-{datetime.now().strftime('%Y%m%d')}                        ║
╚{separator}╝
"""
    
    return output


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

