"""
Shell execution tools for the Modern AI Agent.
"""
import subprocess
from pathlib import Path
from .tool_decorator import tool

@tool(
    description="Executa um comando shell único (ex: ls, pwd, git status). CUIDADO: use apenas comandos seguros de leitura.",
    parameters={
        "command": {"type": "string", "description": "Comando shell a executar (ex: 'ls -la', 'pwd', 'git status')"},
        "timeout": {"type": "integer", "description": "Timeout em segundos (padrão: 30)", "default": 30}
    },
    required=["command"],
    complexity="simple"
)
def run_command(command: str, workspace: Path, timeout: int = 30) -> str:
    """Executa um comando shell único."""
    dangerous_commands = ['rm -rf', 'mkfs', 'dd', ':(){:|:&};:', 'fork bomb', '>(', '/dev/sda', 'mv / ', 'chmod -R 777 /', '> /dev/sda', 'wget http', 'curl http']
    if any(d in command for d in dangerous_commands):
        return f"✗ BLOQUEADO: Comando potencialmente perigoso detectado."
    try:
        result = subprocess.run(command, shell=True, cwd=str(workspace), capture_output=True, text=True, timeout=timeout)
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
def run_script(script: str, workspace: Path, shell: str = "bash", timeout: int = 60) -> str:
    """Executa um script shell completo."""
    allowed_shells = ['bash', 'sh', 'zsh', 'dash']
    if shell not in allowed_shells:
        return f"✗ Shell não permitido: {shell}. Use: {', '.join(allowed_shells)}"
    dangerous_patterns = ['rm -rf /', 'rm -rf *', 'mkfs', 'dd if=', 'dd of=/dev', ':(){:|:&};:', '> /dev/sda', 'chmod -R 777 /', 'wget http://', 'curl http://']
    if any(d in script for d in dangerous_patterns):
        return f"✗ BLOQUEADO: Padrão perigoso detectado no script."
    try:
        result = subprocess.run([shell, '-c', script], cwd=str(workspace), capture_output=True, text=True, timeout=timeout)
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
