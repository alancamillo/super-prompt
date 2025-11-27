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
    description="Cria um novo arquivo ou adapta um arquivo existente. Se o arquivo já existe, tenta adaptar ao invés de sobrescrever.",
    parameters={
        "filepath": {"type": "string", "description": "Caminho do arquivo a criar"},
        "content": {"type": "string", "description": "Conteúdo completo a escrever"}
    },
    required=["filepath", "content"],
    complexity="simple"
)
def write_file(filepath: str, content: str, code_agent: CodeAgent, workspace: Path) -> str:
    """Escreve um arquivo com adaptação inteligente se já existir."""
    try:
        file_path = workspace / filepath
        
        # Se arquivo não existe, cria normalmente
        if not file_path.exists():
            code_agent.write_file(filepath, content, show_preview=False)
            return f"✓ Arquivo {filepath} CRIADO com sucesso."
        
        # Arquivo existe - tenta adaptar
        try:
            existing_content = code_agent.read_file(filepath)
            existing_lines = existing_content.splitlines(keepends=True)
            new_lines = content.splitlines(keepends=True)
            
            # Análise inteligente da diferença
            existing_text = existing_content.strip()
            new_text = content.strip()
            
            # Caso 1: Novo conteúdo é apenas uma extensão do existente (adiciona no final)
            # Remove espaços em branco no final para comparação
            existing_clean = existing_text.rstrip()
            new_clean = new_text.rstrip()
            
            if new_clean.startswith(existing_clean) and len(new_clean) > len(existing_clean):
                additional_content = new_clean[len(existing_clean):].strip()
                if additional_content:
                    # Adiciona o conteúdo extra no final
                    code_agent.create_backup(filepath)
                    with open(file_path, 'a', encoding='utf-8') as f:
                        if not existing_content.endswith('\n') and not existing_content.endswith('\r\n'):
                            f.write('\n')
                        f.write(additional_content)
                        if not additional_content.endswith('\n'):
                            f.write('\n')
                    return f"✓ Arquivo {filepath} ADAPTADO: conteúdo adicional adicionado ao final. Backup criado."
            
            # Caso 2: Conteúdo é idêntico
            if existing_text == new_text:
                return f"ℹ️ Arquivo {filepath} já contém exatamente o conteúdo solicitado. Nenhuma mudança necessária."
            
            # Caso 3: Mudança pequena (poucas linhas diferentes)
            existing_set = set(existing_lines)
            new_set = set(new_lines)
            diff_lines = len(new_set.symmetric_difference(existing_set))
            total_lines = max(len(existing_lines), len(new_lines))
            
            if diff_lines <= 3 and total_lines > 5:
                # Mudança pequena - fornece informações para edição manual
                # IMPORTANTE: O prefixo "🚫 BLOQUEIO:" é detectado pelo sistema de auto-replanejamento
                return (
                    f"🚫 BLOQUEIO: Arquivo '{filepath}' JÁ EXISTE com conteúdo similar.\n\n"
                    f"⚠️ write_file é para CRIAR arquivos NOVOS. Este arquivo já existe!\n"
                    f"📊 Diferenças detectadas: ~{diff_lines} linhas (mudança pequena)\n\n"
                    f"✅ USE UMA DESTAS FERRAMENTAS:\n\n"
                    f"  📝 update_file(\"{filepath}\", new_content, \"motivo\")\n"
                    f"     → Substitui o conteúdo mantendo backup\n\n"
                    f"  ➕ ensure_lines(\"{filepath}\", \"linhas\", \"motivo\")\n"
                    f"     → Adiciona só o que falta\n\n"
                    f"  ✏️ edit_lines(\"{filepath}\", start, end, content)\n"
                    f"     → Edita linhas específicas\n\n"
                    f"  🔍 search_replace(\"{filepath}\", busca, substitui)\n"
                    f"     → Substitui texto específico\n\n"
                    f"📝 Conteúdo atual:\n"
                    f"{''.join(existing_lines[:10])}"
                    f"{'...' if len(existing_lines) > 10 else ''}"
                )
            
            # Caso 4: Mudança significativa - fornece informações detalhadas
            # IMPORTANTE: O prefixo "🚫 BLOQUEIO:" é detectado pelo sistema de auto-replanejamento
            return (
                f"🚫 BLOQUEIO: Arquivo '{filepath}' JÁ EXISTE com conteúdo diferente.\n\n"
                f"⚠️ write_file é para CRIAR arquivos NOVOS. Este arquivo já existe!\n\n"
                f"📊 Análise:\n"
                f"  - Arquivo existente: {len(existing_lines)} linhas\n"
                f"  - Novo conteúdo: {len(new_lines)} linhas\n\n"
                f"✅ USE UMA DESTAS FERRAMENTAS DE EDIÇÃO:\n\n"
                f"  📝 update_file(\"{filepath}\", new_content, reason)\n"
                f"     → Substitui o conteúdo do arquivo existente\n"
                f"     → Cria backup automático\n"
                f"     → Mostra comparação antes/depois\n\n"
                f"  ➕ ensure_lines(\"{filepath}\", \"linha1\\nlinha2\", reason)\n"
                f"     → Adiciona APENAS linhas que faltam\n"
                f"     → Mantém conteúdo existente\n"
                f"     → Ideal para requirements.txt\n\n"
                f"  ✏️ edit_lines(\"{filepath}\", start, end, content)\n"
                f"     → Edita linhas específicas (precisa saber quais)\n\n"
                f"  ➕ insert_lines(\"{filepath}\", after_line, content)\n"
                f"     → Insere após uma linha específica\n\n"
                f"📝 Conteúdo atual do arquivo:\n"
                f"{''.join(existing_lines[:15])}"
                f"{'...' if len(existing_lines) > 15 else ''}"
            )
            
        except Exception as read_error:
            # Se não conseguir ler, retorna mensagem genérica
            return (
                f"⚠️ Arquivo '{filepath}' JÁ EXISTE, mas não foi possível analisar o conteúdo.\n"
                f"Erro ao ler: {read_error}\n\n"
                f"💡 Use 'read_file(\"{filepath}\")' para ver o conteúdo atual,\n"
                f"ou 'force_write_file(\"{filepath}\", content, reason=\"...\")' para sobrescrever."
            )
            
    except Exception as e:
        return f"✗ Erro ao processar {filepath}: {e}"

@tool(
    description="""📝 ATUALIZA um arquivo EXISTENTE de forma inteligente.

USE ESTA FERRAMENTA quando:
- O arquivo JÁ EXISTE e você quer MODIFICAR seu conteúdo
- Você recebeu um bloqueio de write_file
- Você quer substituir o conteúdo de forma segura

A ferramenta:
1. Lê o arquivo atual
2. Cria backup automático
3. Substitui pelo novo conteúdo
4. Retorna comparação do antes/depois

DIFERENTE de write_file (que só cria novos) e force_write_file (que não mostra comparação).""",
    parameters={
        "filepath": {"type": "string", "description": "Caminho do arquivo EXISTENTE a atualizar"},
        "new_content": {"type": "string", "description": "Novo conteúdo completo para o arquivo"},
        "reason": {"type": "string", "description": "Motivo da atualização (para log/audit)"}
    },
    required=["filepath", "new_content", "reason"],
    complexity="simple"
)
def update_file(filepath: str, new_content: str, reason: str, code_agent: CodeAgent, workspace: Path) -> str:
    """Atualiza um arquivo existente de forma inteligente."""
    try:
        file_path = workspace / filepath
        
        # Verifica se arquivo existe
        if not file_path.exists():
            return (
                f"⚠️ Arquivo '{filepath}' NÃO EXISTE.\n\n"
                f"💡 Use 'write_file(\"{filepath}\", content)' para CRIAR um novo arquivo."
            )
        
        # Lê conteúdo atual
        existing_content = code_agent.read_file(filepath)
        existing_lines = existing_content.splitlines()
        new_lines = new_content.splitlines()
        
        # Verifica se é idêntico
        if existing_content.strip() == new_content.strip():
            return f"ℹ️ Arquivo '{filepath}' já contém exatamente o conteúdo solicitado. Nenhuma mudança necessária."
        
        # Cria backup e atualiza
        code_agent.create_backup(filepath)
        code_agent.write_file(filepath, new_content, show_preview=False)
        
        # Gera resumo das mudanças
        return (
            f"✅ Arquivo '{filepath}' ATUALIZADO com sucesso!\n\n"
            f"📊 Resumo:\n"
            f"  - Linhas anteriores: {len(existing_lines)}\n"
            f"  - Linhas novas: {len(new_lines)}\n"
            f"  - Motivo: {reason}\n"
            f"  - Backup: criado automaticamente\n\n"
            f"📝 Conteúdo anterior (primeiras 5 linhas):\n"
            f"{''.join(l + chr(10) for l in existing_lines[:5])}"
            f"{'...' if len(existing_lines) > 5 else ''}\n\n"
            f"📝 Conteúdo novo (primeiras 5 linhas):\n"
            f"{''.join(l + chr(10) for l in new_lines[:5])}"
            f"{'...' if len(new_lines) > 5 else ''}"
        )
        
    except Exception as e:
        return f"✗ Erro ao atualizar {filepath}: {e}"


@tool(
    description="""➕ GARANTE que certas linhas existam em um arquivo.

USE ESTA FERRAMENTA quando:
- Você quer ADICIONAR linhas a um arquivo existente
- Você quer garantir que certas dependências estejam no requirements.txt
- Você NÃO quer sobrescrever o arquivo inteiro

A ferramenta:
1. Lê o arquivo atual
2. Verifica quais linhas já existem
3. Adiciona APENAS as linhas que faltam
4. Mantém o conteúdo existente intacto

Exemplo: ensure_lines("requirements.txt", "fastapi\\nuvicorn", "adicionar deps FastAPI")""",
    parameters={
        "filepath": {"type": "string", "description": "Caminho do arquivo"},
        "lines_to_ensure": {"type": "string", "description": "Linhas que devem existir (separadas por \\n)"},
        "reason": {"type": "string", "description": "Motivo da adição"}
    },
    required=["filepath", "lines_to_ensure", "reason"],
    complexity="simple"
)
def ensure_lines(filepath: str, lines_to_ensure: str, reason: str, code_agent: CodeAgent, workspace: Path) -> str:
    """Garante que certas linhas existam em um arquivo."""
    try:
        file_path = workspace / filepath
        
        # Se arquivo não existe, cria com as linhas
        if not file_path.exists():
            code_agent.write_file(filepath, lines_to_ensure, show_preview=False)
            return f"✅ Arquivo '{filepath}' CRIADO com as linhas solicitadas. Motivo: {reason}"
        
        # Lê conteúdo atual
        existing_content = code_agent.read_file(filepath)
        existing_lines_set = set(line.strip() for line in existing_content.splitlines() if line.strip())
        
        # Verifica quais linhas precisam ser adicionadas
        new_lines = [line.strip() for line in lines_to_ensure.splitlines() if line.strip()]
        lines_to_add = [line for line in new_lines if line not in existing_lines_set]
        
        if not lines_to_add:
            return (
                f"ℹ️ Todas as linhas já existem em '{filepath}'.\n\n"
                f"✅ Linhas verificadas:\n"
                + "\n".join(f"  ✓ {line}" for line in new_lines)
            )
        
        # Adiciona as linhas que faltam
        code_agent.create_backup(filepath)
        with open(file_path, 'a', encoding='utf-8') as f:
            if not existing_content.endswith('\n'):
                f.write('\n')
            for line in lines_to_add:
                f.write(line + '\n')
        
        return (
            f"✅ Linhas adicionadas a '{filepath}'!\n\n"
            f"➕ Linhas ADICIONADAS:\n"
            + "\n".join(f"  + {line}" for line in lines_to_add) +
            f"\n\n✓ Linhas que já existiam:\n"
            + "\n".join(f"  ✓ {line}" for line in new_lines if line not in lines_to_add) +
            f"\n\n📝 Motivo: {reason}\n"
            f"💾 Backup: criado automaticamente"
        )
        
    except Exception as e:
        return f"✗ Erro ao processar {filepath}: {e}"


@tool(
    description="⚠️ Sobrescreve um arquivo EXISTENTE forçadamente. Use APENAS como ÚLTIMO RECURSO. Cria backup automático.",
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
