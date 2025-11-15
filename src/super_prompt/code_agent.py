#!/usr/bin/env python3
"""
AI Code Agent - Sistema interativo de edição de código
Similar ao Gemini CLI e Claude Desktop
"""

from pathlib import Path
from typing import Optional, List, Tuple, Set
from datetime import datetime
import difflib
import shutil
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box
from rich.text import Text


@dataclass
class FileEdit:
    """Representa uma edição a ser aplicada em um arquivo"""
    start_line: int
    end_line: int
    new_content: str
    description: str = ""


class CodeAgent:
    """
    Agente de código inteligente para edição interativa de arquivos.
    
    Funcionalidades:
    - Edição de arquivos com preview e aprovação
    - Diffs coloridos
    - Backups automáticos
    - Syntax highlighting
    - Gestão inteligente de índices de linha em múltiplas edições
    """
    
    def __init__(self, workspace: str = "."):
        """
        Inicializa o Code Agent.
        
        Args:
            workspace: Diretório raiz do workspace
        """
        self.workspace = Path(workspace).resolve()
        self.backup_dir = self.workspace / ".code_agent_backups"
        self.console = Console()
        self.backup_dir.mkdir(exist_ok=True)
        
    def read_file(self, filepath: str) -> str:
        """
        Lê o conteúdo de um arquivo.
        
        Args:
            filepath: Caminho do arquivo relativo ao workspace
            
        Returns:
            Conteúdo do arquivo como string
            
        Raises:
            FileNotFoundError: Se o arquivo não existir
        """
        file_path = self.workspace / filepath
        
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def write_file(
        self, 
        filepath: str, 
        content: str, 
        show_preview: bool = True
    ) -> bool:
        """
        Escreve conteúdo em um arquivo com preview opcional.
        
        Args:
            filepath: Caminho do arquivo
            content: Conteúdo a escrever
            show_preview: Se True, mostra diff e pede confirmação
            
        Returns:
            True se a operação foi bem-sucedida
        """
        file_path = self.workspace / filepath
        file_exists = file_path.exists()
        
        # Se o arquivo existe, cria backup e mostra diff
        if file_exists:
            old_content = self.read_file(filepath)
            
            if show_preview:
                self.show_diff(filepath, old_content, content)
                
                if not Confirm.ask("💾 Aplicar estas mudanças?", default=False):
                    self.console.print("[yellow]❌ Operação cancelada pelo usuário[/yellow]")
                    return False
            
            # Cria backup antes de modificar
            self.create_backup(filepath)
        else:
            # Arquivo novo
            if show_preview:
                self._show_new_file_preview(filepath, content)
                
                if not Confirm.ask("💾 Criar este arquivo?", default=False):
                    self.console.print("[yellow]❌ Operação cancelada pelo usuário[/yellow]")
                    return False
        
        # Cria diretórios pai se necessário
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Escreve o arquivo
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        action = "atualizado" if file_exists else "criado"
        self.console.print(f"[green]✓ Arquivo {action} com sucesso: {filepath}[/green]")
        return True
    
    def show_diff(self, filepath: str, old_content: str, new_content: str) -> None:
        """
        Mostra diferenças entre duas versões de um arquivo.
        
        Args:
            filepath: Nome do arquivo (para display)
            old_content: Conteúdo antigo
            new_content: Conteúdo novo
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"{filepath} (original)",
            tofile=f"{filepath} (novo)",
            lineterm=''
        )
        
        diff_text = ''.join(diff)
        
        if not diff_text:
            self.console.print("[yellow]ℹ️  Nenhuma mudança detectada[/yellow]")
            return
        
        # Syntax highlighting para diff
        syntax = Syntax(
            diff_text,
            "diff",
            theme="monokai",
            line_numbers=False,
            word_wrap=False
        )
        
        panel = Panel(
            syntax,
            title="📊 Diferenças Detectadas",
            border_style="cyan",
            box=box.ROUNDED
        )
        
        self.console.print(panel)
    
    def _show_new_file_preview(self, filepath: str, content: str) -> None:
        """Mostra preview de um arquivo novo a ser criado"""
        # Detecta linguagem pela extensão
        suffix = Path(filepath).suffix.lstrip('.')
        language = suffix if suffix else "text"
        
        syntax = Syntax(
            content,
            language,
            theme="monokai",
            line_numbers=True,
            word_wrap=False
        )
        
        panel = Panel(
            syntax,
            title=f"📄 Novo Arquivo: {filepath}",
            border_style="green",
            box=box.ROUNDED
        )
        
        self.console.print(panel)
    
    def create_backup(self, filepath: str) -> Path:
        """
        Cria backup de um arquivo com timestamp.
        
        Args:
            filepath: Caminho do arquivo a fazer backup
            
        Returns:
            Path do arquivo de backup criado
        """
        file_path = self.workspace / filepath
        
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        
        # Nome do backup com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.backup"
        backup_path = self.backup_dir / backup_name
        
        # Copia o arquivo
        shutil.copy2(file_path, backup_path)
        
        self.console.print(f"[dim]📦 Backup criado: {backup_name}[/dim]")
        return backup_path
    
    def search_replace(
        self,
        filepath: str,
        search: str,
        replace: str,
        show_preview: bool = True
    ) -> bool:
        """
        Busca e substitui texto em um arquivo.
        
        Args:
            filepath: Caminho do arquivo
            search: Texto a buscar
            replace: Texto substituto
            show_preview: Se True, mostra diff antes de aplicar
            
        Returns:
            True se a operação foi bem-sucedida
        """
        content = self.read_file(filepath)
        
        if search not in content:
            self.console.print(f"[yellow]⚠️  Texto '{search}' não encontrado em {filepath}[/yellow]")
            return False
        
        # Conta ocorrências
        count = content.count(search)
        self.console.print(f"[cyan]🔍 Encontradas {count} ocorrência(s) de '{search}'[/cyan]")
        
        # Substitui
        new_content = content.replace(search, replace)
        
        # Escreve com preview
        return self.write_file(filepath, new_content, show_preview)
    
    def edit_lines(
        self,
        filepath: str,
        start_line: int,
        end_line: int,
        new_content: str,
        show_preview: bool = True
    ) -> bool:
        """
        Edita linhas específicas de um arquivo.
        
        Args:
            filepath: Caminho do arquivo
            start_line: Linha inicial (1-indexed)
            end_line: Linha final (1-indexed, inclusiva)
            new_content: Novo conteúdo para as linhas
            show_preview: Se True, mostra diff antes de aplicar
            
        Returns:
            True se a operação foi bem-sucedida
        """
        content = self.read_file(filepath)
        lines = content.splitlines(keepends=True)
        
        # Validação de índices
        if start_line < 1 or end_line < 1:
            self.console.print("[red]❌ Números de linha devem ser >= 1[/red]")
            return False
        
        if start_line > len(lines) + 1:
            self.console.print(f"[red]❌ Linha inicial {start_line} está além do arquivo (tem {len(lines)} linhas)[/red]")
            return False
        
        if end_line > len(lines) + 1:
            self.console.print(f"[red]❌ Linha final {end_line} está além do arquivo (tem {len(lines)} linhas)[/red]")
            return False
        
        # Mostra contexto das linhas que serão editadas
        if show_preview:
            self._show_line_context(filepath, lines, start_line, end_line)
        
        # Ajusta índices para 0-based
        start_idx = start_line - 1
        end_idx = end_line
        
        # Garante que new_content termina com newline se não for vazio
        if new_content and not new_content.endswith('\n'):
            new_content += '\n'
        
        # Constrói novo conteúdo
        new_lines = lines[:start_idx] + [new_content] + lines[end_idx:]
        new_file_content = ''.join(new_lines)
        
        # Escreve com preview
        return self.write_file(filepath, new_file_content, show_preview)
    
    def delete_lines(
        self,
        filepath: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        line_indices: Optional[List[int]] = None,
        show_preview: bool = True
    ) -> bool:
        """
        Remove linhas específicas de um arquivo.
        
        Pode ser usado de duas formas:
        1. Range: delete_lines('file.py', start_line=5, end_line=10)  # Remove linhas 5-10
        2. Índices específicos: delete_lines('file.py', line_indices=[0, 10, 23])  # Remove linhas 1, 11, 24
        
        Args:
            filepath: Caminho do arquivo
            start_line: Linha inicial do range (1-indexed, inclusiva)
            end_line: Linha final do range (1-indexed, inclusiva)
            line_indices: Lista de índices de linhas para remover (0-indexed)
            show_preview: Se True, mostra preview antes de aplicar
            
        Returns:
            True se a operação foi bem-sucedida
            
        Raises:
            ValueError: Se parâmetros inválidos
        """
        # Validação de parâmetros
        if (start_line is None and end_line is None and line_indices is None):
            self.console.print("[red]❌ Erro: Deve fornecer start_line/end_line OU line_indices[/red]")
            return False
        
        if (start_line is not None or end_line is not None) and line_indices is not None:
            self.console.print("[red]❌ Erro: Use range OU line_indices, não ambos[/red]")
            return False
        
        content = self.read_file(filepath)
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)
        
        # Determina quais linhas remover
        lines_to_remove: Set[int] = set()
        
        if line_indices is not None:
            # Modo: índices específicos (0-indexed)
            for idx in line_indices:
                if idx < 0 or idx >= total_lines:
                    self.console.print(f"[red]❌ Índice {idx} inválido (arquivo tem {total_lines} linhas, índices 0-{total_lines-1})[/red]")
                    return False
                lines_to_remove.add(idx)
        else:
            # Modo: range (1-indexed)
            if start_line is None or end_line is None:
                self.console.print("[red]❌ Erro: start_line e end_line são obrigatórios no modo range[/red]")
                return False
            
            if start_line < 1 or end_line < 1:
                self.console.print("[red]❌ Números de linha devem ser >= 1[/red]")
                return False
            
            if start_line > total_lines:
                self.console.print(f"[red]❌ Linha inicial {start_line} está além do arquivo (tem {total_lines} linhas)[/red]")
                return False
            
            if end_line > total_lines:
                self.console.print(f"[red]❌ Linha final {end_line} está além do arquivo (tem {total_lines} linhas)[/red]")
                return False
            
            if start_line > end_line:
                self.console.print(f"[red]❌ Linha inicial {start_line} maior que linha final {end_line}[/red]")
                return False
            
            # Converte para 0-indexed e adiciona ao set
            for line_num in range(start_line, end_line + 1):
                lines_to_remove.add(line_num - 1)
        
        if not lines_to_remove:
            self.console.print("[yellow]⚠️ Nenhuma linha para remover[/yellow]")
            return False
        
        # Mostra preview se solicitado
        if show_preview:
            self._show_delete_preview(filepath, lines, lines_to_remove)
            
            from rich.prompt import Confirm
            if not Confirm.ask("\n[yellow]Deseja aplicar esta remoção?[/yellow]", default=True):
                self.console.print("[yellow]Operação cancelada pelo usuário[/yellow]")
                return False
        
        # Remove linhas (em ordem reversa para não invalidar índices)
        sorted_indices = sorted(lines_to_remove, reverse=True)
        new_lines = lines.copy()
        
        for idx in sorted_indices:
            del new_lines[idx]
        
        # Reconstrói conteúdo
        new_file_content = ''.join(new_lines)
        
        # Cria backup antes de modificar
        self.create_backup(filepath)
        
        # Escreve arquivo modificado
        return self.write_file(filepath, new_file_content, show_preview=False)
    
    def _show_delete_preview(
        self,
        filepath: str,
        lines: List[str],
        lines_to_remove: Set[int]
    ) -> None:
        """Mostra preview das linhas que serão removidas"""
        context = 2  # Linhas de contexto
        
        # Determina range com contexto
        min_idx = min(lines_to_remove)
        max_idx = max(lines_to_remove)
        
        context_start = max(0, min_idx - context)
        context_end = min(len(lines) - 1, max_idx + context)
        
        # Constrói texto com marcação
        display_lines = []
        for i in range(context_start, context_end + 1):
            line_num = f"{i + 1:4d}"  # 1-indexed para display
            line_content = lines[i].rstrip('\n')
            
            if i in lines_to_remove:
                # Linha que será removida
                display_lines.append(f"[red]-{line_num}| {line_content}[/red]")
            else:
                # Contexto
                display_lines.append(f"[dim] {line_num}| {line_content}[/dim]")
        
        removed_count = len(lines_to_remove)
        removed_range = f"linhas {sorted(lines_to_remove)[0] + 1}-{sorted(lines_to_remove)[-1] + 1}" if removed_count > 1 else f"linha {sorted(lines_to_remove)[0] + 1}"
        
        panel = Panel(
            '\n'.join(display_lines),
            title=f"🗑️  Remover {removed_count} {removed_range} de {filepath}",
            border_style="red",
            box=box.ROUNDED
        )
        
        self.console.print(panel)
    
    def _show_line_context(
        self,
        filepath: str,
        lines: List[str],
        start_line: int,
        end_line: int
    ) -> None:
        """Mostra contexto das linhas que serão editadas"""
        context = 2  # Linhas de contexto antes e depois
        
        # Determina range com contexto
        context_start = max(1, start_line - context)
        context_end = min(len(lines), end_line + context)
        
        # Constrói texto com marcação
        display_lines = []
        for i in range(context_start, context_end + 1):
            if i <= len(lines):
                line_num = f"{i:4d}"
                line_content = lines[i - 1].rstrip('\n')
                
                if start_line <= i <= end_line:
                    # Linha que será editada
                    display_lines.append(f"[red]-{line_num}| {line_content}[/red]")
                else:
                    # Contexto
                    display_lines.append(f"[dim] {line_num}| {line_content}[/dim]")
        
        panel = Panel(
            '\n'.join(display_lines),
            title=f"📍 Contexto: {filepath} (linhas {start_line}-{end_line})",
            border_style="yellow",
            box=box.ROUNDED
        )
        
        self.console.print(panel)
    
    def apply_edits(
        self,
        filepath: str,
        edits: List[FileEdit],
        show_preview: bool = True
    ) -> bool:
        """
        Aplica múltiplas edições em um arquivo de forma segura.
        
        IMPORTANTE: As edições são aplicadas em ordem reversa (de baixo para cima)
        para evitar invalidação de índices de linha.
        
        Args:
            filepath: Caminho do arquivo
            edits: Lista de edições a aplicar
            show_preview: Se True, mostra preview consolidado
            
        Returns:
            True se todas as operações foram bem-sucedidas
        """
        if not edits:
            self.console.print("[yellow]⚠️  Nenhuma edição para aplicar[/yellow]")
            return False
        
        # Ordena edições por linha (do final para o início)
        sorted_edits = sorted(edits, key=lambda e: e.start_line, reverse=True)
        
        self.console.print(f"[cyan]📝 Aplicando {len(edits)} edição(ões) em {filepath}[/cyan]")
        
        # Lê conteúdo atual
        content = self.read_file(filepath)
        lines = content.splitlines(keepends=True)
        
        # Valida todas as edições primeiro
        for idx, edit in enumerate(sorted_edits, 1):
            if edit.start_line < 1 or edit.end_line < 1:
                self.console.print(f"[red]❌ Edição {idx}: Números de linha devem ser >= 1[/red]")
                return False
            
            if edit.start_line > len(lines) + 1 or edit.end_line > len(lines) + 1:
                self.console.print(f"[red]❌ Edição {idx}: Linhas {edit.start_line}-{edit.end_line} estão além do arquivo (tem {len(lines)} linhas)[/red]")
                return False
        
        # Aplica edições em ordem reversa
        for idx, edit in enumerate(sorted_edits, 1):
            start_idx = edit.start_line - 1
            end_idx = edit.end_line
            
            # Garante newline
            new_content = edit.new_content
            if new_content and not new_content.endswith('\n'):
                new_content += '\n'
            
            # Aplica edição
            lines = lines[:start_idx] + [new_content] + lines[end_idx:]
            
            desc = f" ({edit.description})" if edit.description else ""
            self.console.print(f"[dim]  ✓ Edição {idx}/{len(sorted_edits)}: linhas {edit.start_line}-{edit.end_line}{desc}[/dim]")
        
        # Constrói conteúdo final
        new_file_content = ''.join(lines)
        
        # Escreve com preview
        return self.write_file(filepath, new_file_content, show_preview)
    
    def list_files(self, pattern: str = "*") -> None:
        """
        Lista arquivos do workspace com metadados formatados.
        
        Args:
            pattern: Padrão glob para filtrar arquivos (ex: "*.py", "src/**/*.js")
        """
        # Busca arquivos
        if "**" in pattern:
            files = list(self.workspace.rglob(pattern.replace("**/", "")))
        else:
            files = list(self.workspace.glob(pattern))
        
        # Filtra apenas arquivos (não diretórios)
        files = [f for f in files if f.is_file()]
        
        # Exclui backups
        files = [f for f in files if ".code_agent_backups" not in str(f)]
        
        if not files:
            self.console.print(f"[yellow]⚠️  Nenhum arquivo encontrado com padrão '{pattern}'[/yellow]")
            return
        
        # Cria tabela
        table = Table(
            title=f"📁 Arquivos no Workspace ({len(files)} encontrado(s))",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("📄 Arquivo", style="green", no_wrap=False)
        table.add_column("📏 Tamanho", justify="right", style="yellow")
        table.add_column("📅 Modificado", style="blue")
        table.add_column("🔤 Linhas", justify="right", style="magenta")
        
        # Adiciona arquivos à tabela
        for file_path in sorted(files):
            rel_path = file_path.relative_to(self.workspace)
            size = file_path.stat().st_size
            
            # Formata tamanho
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            
            # Data de modificação
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            mtime_str = mtime.strftime("%Y-%m-%d %H:%M")
            
            # Conta linhas (se for texto)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = sum(1 for _ in f)
                lines_str = str(lines)
            except:
                lines_str = "N/A"
            
            table.add_row(str(rel_path), size_str, mtime_str, lines_str)
        
        self.console.print(table)
    
    def show_file(self, filepath: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> None:
        """
        Mostra conteúdo de um arquivo com syntax highlighting.
        
        Args:
            filepath: Caminho do arquivo
            start_line: Linha inicial para mostrar (opcional)
            end_line: Linha final para mostrar (opcional)
        """
        content = self.read_file(filepath)
        
        # Se especificou range de linhas
        if start_line is not None or end_line is not None:
            lines = content.splitlines()
            start = (start_line - 1) if start_line else 0
            end = end_line if end_line else len(lines)
            content = '\n'.join(lines[start:end])
        
        # Detecta linguagem
        suffix = Path(filepath).suffix.lstrip('.')
        language = suffix if suffix else "text"
        
        syntax = Syntax(
            content,
            language,
            theme="monokai",
            line_numbers=True,
            word_wrap=False,
            line_range=(start_line, end_line) if start_line else None
        )
        
        range_info = f" (linhas {start_line}-{end_line})" if start_line else ""
        panel = Panel(
            syntax,
            title=f"📄 {filepath}{range_info}",
            border_style="cyan",
            box=box.ROUNDED
        )
        
        self.console.print(panel)


def demo():
    """Demonstração interativa do Code Agent"""
    console = Console()
    agent = CodeAgent()
    
    # Banner
    console.print(Panel.fit(
        "[bold cyan]🤖 AI Code Agent[/bold cyan]\n"
        "[dim]Sistema interativo de edição de código[/dim]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    
    while True:
        # Menu principal
        console.print("\n[bold cyan]═══ MENU PRINCIPAL ═══[/bold cyan]")
        console.print("[1] 📄 Criar novo arquivo")
        console.print("[2] ✏️  Editar arquivo completo")
        console.print("[3] 🔍 Buscar e substituir")
        console.print("[4] 📝 Editar linhas específicas")
        console.print("[5] 🔄 Aplicar múltiplas edições")
        console.print("[6] 👁️  Visualizar arquivo")
        console.print("[7] 📁 Listar arquivos")
        console.print("[8] 🧪 Teste de múltiplas edições")
        console.print("[9] ❌ Sair")
        
        choice = Prompt.ask(
            "\n[bold yellow]Escolha uma opção[/bold yellow]",
            choices=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
            default="9"
        )
        
        try:
            if choice == "1":
                # Criar arquivo
                filepath = Prompt.ask("📄 Nome do arquivo")
                console.print("[dim]Digite o conteúdo (termine com Ctrl+D ou linha vazia):[/dim]")
                
                lines = []
                try:
                    while True:
                        line = input()
                        if not line:
                            break
                        lines.append(line)
                except EOFError:
                    pass
                
                content = '\n'.join(lines)
                agent.write_file(filepath, content, show_preview=True)
            
            elif choice == "2":
                # Editar arquivo completo
                filepath = Prompt.ask("📄 Nome do arquivo")
                
                try:
                    current = agent.read_file(filepath)
                    console.print(f"[cyan]Conteúdo atual tem {len(current.splitlines())} linhas[/cyan]")
                except FileNotFoundError:
                    console.print("[yellow]Arquivo não existe. Criando novo.[/yellow]")
                
                console.print("[dim]Digite o novo conteúdo (termine com linha vazia):[/dim]")
                lines = []
                while True:
                    line = input()
                    if not line:
                        break
                    lines.append(line)
                
                content = '\n'.join(lines)
                agent.write_file(filepath, content, show_preview=True)
            
            elif choice == "3":
                # Buscar e substituir
                filepath = Prompt.ask("📄 Nome do arquivo")
                search = Prompt.ask("🔍 Texto a buscar")
                replace = Prompt.ask("✏️  Texto substituto")
                
                agent.search_replace(filepath, search, replace, show_preview=True)
            
            elif choice == "4":
                # Editar linhas específicas
                filepath = Prompt.ask("📄 Nome do arquivo")
                
                # Mostra arquivo primeiro
                agent.show_file(filepath)
                
                start = int(Prompt.ask("📍 Linha inicial"))
                end = int(Prompt.ask("📍 Linha final"))
                
                console.print("[dim]Digite o novo conteúdo para estas linhas (termine com linha vazia):[/dim]")
                lines = []
                while True:
                    line = input()
                    if not line:
                        break
                    lines.append(line)
                
                content = '\n'.join(lines)
                agent.edit_lines(filepath, start, end, content, show_preview=True)
            
            elif choice == "5":
                # Múltiplas edições
                filepath = Prompt.ask("📄 Nome do arquivo")
                
                # Mostra arquivo
                agent.show_file(filepath)
                
                edits = []
                console.print("[cyan]📝 Adicionando edições (deixe descrição vazia para finalizar)[/cyan]")
                
                while True:
                    desc = Prompt.ask("Descrição da edição (ou vazio para finalizar)", default="")
                    if not desc:
                        break
                    
                    start = int(Prompt.ask("  Linha inicial"))
                    end = int(Prompt.ask("  Linha final"))
                    
                    console.print("  [dim]Novo conteúdo (linha vazia para finalizar):[/dim]")
                    lines = []
                    while True:
                        line = input("  ")
                        if not line:
                            break
                        lines.append(line)
                    
                    content = '\n'.join(lines)
                    edits.append(FileEdit(start, end, content, desc))
                    console.print(f"  [green]✓ Edição adicionada: {desc}[/green]")
                
                if edits:
                    agent.apply_edits(filepath, edits, show_preview=True)
            
            elif choice == "6":
                # Visualizar arquivo
                filepath = Prompt.ask("📄 Nome do arquivo")
                
                if Confirm.ask("Mostrar apenas um range de linhas?", default=False):
                    start = int(Prompt.ask("Linha inicial"))
                    end = int(Prompt.ask("Linha final"))
                    agent.show_file(filepath, start, end)
                else:
                    agent.show_file(filepath)
            
            elif choice == "7":
                # Listar arquivos
                pattern = Prompt.ask("🔍 Padrão de busca", default="*")
                agent.list_files(pattern)
            
            elif choice == "8":
                # Teste de múltiplas edições
                console.print("[bold yellow]🧪 Executando teste de múltiplas edições...[/bold yellow]")
                
                test_file = "test_multiline.py"
                
                # Cria arquivo de teste
                initial_content = '\n'.join([f"# Linha {i}" for i in range(1, 21)])
                console.print(f"[cyan]Criando arquivo de teste com 20 linhas...[/cyan]")
                agent.write_file(test_file, initial_content, show_preview=False)
                
                # Edição 1: Adiciona 2 linhas na posição 5
                console.print("\n[cyan]Edição 1: Adicionando 2 linhas após linha 5[/cyan]")
                agent.edit_lines(
                    test_file,
                    6, 5,  # Inserir após linha 5
                    "# Nova linha A\n# Nova linha B",
                    show_preview=True
                )
                
                # Recarrega e ajusta índices
                console.print("\n[cyan]Edição 2: Editando linha 15 (que agora é linha 17 após inserção)[/cyan]")
                current_content = agent.read_file(test_file)
                current_lines = current_content.splitlines()
                console.print(f"[dim]Arquivo agora tem {len(current_lines)} linhas[/dim]")
                
                # Edita linha 17 (era linha 15 original)
                agent.edit_lines(
                    test_file,
                    17, 17,
                    "# Linha 15 MODIFICADA",
                    show_preview=True
                )
                
                console.print("\n[green]✓ Teste concluído! Verifique o arquivo.[/green]")
                agent.show_file(test_file)
            
            elif choice == "9":
                console.print("\n[bold cyan]👋 Até logo![/bold cyan]")
                break
        
        except FileNotFoundError as e:
            console.print(f"[red]❌ Erro: {e}[/red]")
        except ValueError as e:
            console.print(f"[red]❌ Valor inválido: {e}[/red]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Operação cancelada[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Erro inesperado: {e}[/red]")


if __name__ == "__main__":
    demo()

