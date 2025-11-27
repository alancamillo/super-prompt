"""
Shell execution tools for the Modern AI Agent.
"""
import subprocess
import os
import signal
import time
from pathlib import Path
from .tool_decorator import tool

@tool(
    description="""Executa um comando shell único que termina rapidamente (ex: ls, pwd, git status, pip install).

⚠️ REGRAS IMPORTANTES:
1. NUNCA execute comandos que deixam o processo em HOLDING (bloqueiam indefinidamente):
   - Servidores: uvicorn, python -m http.server, flask run, django runserver, npm start, etc.
   - Processos interativos: python (sem -c), bash (sem -c), vim, nano, etc.
   - Comandos que esperam input: read, cat sem pipe, etc.

2. Se PRECISAR executar um servidor ou processo de longa duração:
   - Use nohup para executar em background: nohup uvicorn app:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
   - SEMPRE salve o PID em arquivo: echo $! > server.pid
   - Exemplo completo: nohup uvicorn app:app --host 0.0.0.0 --port 8000 > server.log 2>&1 & echo $! > server.pid
   - Depois, para parar: kill $(cat server.pid) && rm server.pid

3. Use apenas comandos que terminam rapidamente e retornam resultado.""",
    parameters={
        "command": {"type": "string", "description": "Comando shell a executar (ex: 'ls -la', 'pwd', 'git status', 'pip install fastapi'). Deve terminar rapidamente e não bloquear o processo."},
        "timeout": {"type": "integer", "description": "Timeout em segundos (padrão: 30)", "default": 30}
    },
    required=["command"],
    complexity="simple"
)
def run_command(command: str, workspace: Path, timeout: int = 30) -> str:
    """Executa um comando shell único."""
    # Comandos perigosos que podem causar danos
    dangerous_commands = ['rm -rf', 'mkfs', 'dd', ':(){:|:&};:', 'fork bomb', '>(', '/dev/sda', 'mv / ', 'chmod -R 777 /', '> /dev/sda']
    if any(d in command for d in dangerous_commands):
        return f"✗ BLOQUEADO: Comando potencialmente perigoso detectado."
    
    # Comandos que podem travar o processo (servidores e processos de longa duração)
    blocking_commands = [
        'uvicorn', 'gunicorn', 'python -m http.server', 'flask run', 'django runserver',
        'npm start', 'npm run dev', 'yarn start', 'yarn dev',
        'python app.py', 'python main.py',  # Se for servidor
        'node server.js', 'node app.js',
        'rails server', 'rails s',
        'php -S', 'php artisan serve',
        'jupyter notebook', 'jupyter lab',
        'streamlit run',
        'gradle run', 'mvn spring-boot:run'
    ]
    
    # Verifica se é um comando bloqueante
    command_lower = command.lower()
    is_blocking = any(blocking in command_lower for blocking in blocking_commands)
    
    # Verifica se já está usando nohup e salvando PID corretamente
    has_nohup = 'nohup' in command_lower
    has_background = '&' in command  # Qualquer & no comando indica background
    has_pid_save = 'echo $!' in command and '.pid' in command  # echo $! E .pid no mesmo comando
    
    # Se está usando nohup com background E salvando PID, permite execução
    if is_blocking and has_nohup and has_background and has_pid_save:
        # Executa o comando e adiciona observação
        try:
            result = subprocess.run(command, shell=True, cwd=str(workspace), capture_output=True, text=True, timeout=timeout)
            output = f"✓ Servidor iniciado em BACKGROUND: {command}\nExit code: {result.returncode}\n"
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            
            # Adiciona observação importante
            output += (
                f"\n⚠️ OBSERVAÇÃO IMPORTANTE:\n"
                f"O servidor foi iniciado em background. Quando terminar a operação,\n"
                f"use 'stop_background_process' para parar o servidor:\n"
                f"   stop_background_process(\"server.pid\")\n"
            )
            return output
        except subprocess.TimeoutExpired:
            return f"✗ TIMEOUT ao iniciar servidor em background. Verifique o comando."
        except Exception as e:
            return f"✗ Erro ao executar comando: {e}"
    
    # Se é bloqueante mas NÃO está configurado corretamente
    if is_blocking and not (has_nohup and has_background and has_pid_save):
        return (
            f"⚠️ AVISO: Este comando pode travar o processo!\n\n"
            f"O comando '{command}' parece ser um servidor ou processo de longa duração que vai bloquear a execução.\n\n"
            f"💡 SOLUÇÃO: Use nohup em background e salve o PID:\n"
            f"   nohup {command} > output.log 2>&1 & echo $! > process.pid\n\n"
            f"📝 Exemplo para uvicorn:\n"
            f"   nohup uvicorn app:app --host 0.0.0.0 --port 8000 > server.log 2>&1 & echo $! > server.pid\n\n"
            f"🛑 Para parar depois:\n"
            f"   stop_background_process(\"process.pid\")\n\n"
            f"Se você realmente precisa executar este comando, modifique-o para usar nohup e salvar o PID."
        )
    
    try:
        result = subprocess.run(command, shell=True, cwd=str(workspace), capture_output=True, text=True, timeout=timeout)
        output = f"✓ Comando executado: {command}\nExit code: {result.returncode}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        return output
    except subprocess.TimeoutExpired:
        return (
            f"✗ TIMEOUT: Comando excedeu {timeout}s de execução.\n\n"
            f"⚠️ Este comando pode ser um processo de longa duração.\n"
            f"Se for um servidor, use nohup em background:\n"
            f"   nohup {command} > output.log 2>&1 & echo $! > process.pid"
        )
    except Exception as e:
        return f"✗ Erro ao executar comando: {e}"

@tool(
    description="""Executa um script shell completo (múltiplas linhas). Use para operações batch que terminam rapidamente.

⚠️ REGRAS IMPORTANTES:
1. NUNCA execute scripts que contenham servidores ou processos de longa duração sem usar nohup:
   - Servidores: uvicorn, flask run, npm start, etc.
   - Processos interativos ou que esperam input

2. Se o script PRECISAR executar um servidor:
   - Use nohup no comando do servidor dentro do script
   - Salve o PID: nohup comando > log.log 2>&1 & echo $! > process.pid
   - Exemplo em script:
     #!/bin/bash
     nohup uvicorn app:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
     echo $! > server.pid
     echo "Servidor iniciado com PID: $(cat server.pid)"

3. Use apenas scripts que terminam rapidamente e retornam resultado.""",
    parameters={
        "script": {"type": "string", "description": "Script shell completo a executar. Deve terminar rapidamente e não bloquear o processo."},
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
    
    # Comandos perigosos
    dangerous_patterns = ['rm -rf /', 'rm -rf *', 'mkfs', 'dd if=', 'dd of=/dev', ':(){:|:&};:', '> /dev/sda', 'chmod -R 777 /']
    if any(d in script for d in dangerous_patterns):
        return f"✗ BLOQUEADO: Padrão perigoso detectado no script."
    
    # Comandos que podem travar o processo
    blocking_commands = [
        'uvicorn', 'gunicorn', 'python -m http.server', 'flask run', 'django runserver',
        'npm start', 'npm run dev', 'yarn start', 'yarn dev',
        'python app.py', 'python main.py',
        'node server.js', 'node app.js',
        'rails server', 'rails s',
        'php -S', 'php artisan serve',
        'jupyter notebook', 'jupyter lab',
        'streamlit run'
    ]
    
    script_lower = script.lower()
    is_blocking = any(blocking in script_lower for blocking in blocking_commands)
    has_nohup = 'nohup' in script_lower
    has_background = '&' in script
    has_pid_save = 'echo $!' in script and '.pid' in script  # Ambos devem estar presentes
    
    # Se está configurado corretamente com nohup, permite e adiciona observação
    if is_blocking and has_nohup and has_background and has_pid_save:
        try:
            result = subprocess.run([shell, '-c', script], cwd=str(workspace), capture_output=True, text=True, timeout=timeout)
            output = f"✓ Script {shell} executado (servidor em background)\nExit code: {result.returncode}\n"
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            
            output += (
                f"\n⚠️ OBSERVAÇÃO IMPORTANTE:\n"
                f"O servidor foi iniciado em background. Quando terminar a operação,\n"
                f"use 'stop_background_process' para parar o servidor.\n"
            )
            return output
        except subprocess.TimeoutExpired:
            return f"✗ TIMEOUT ao executar script. Verifique os comandos."
        except Exception as e:
            return f"✗ Erro ao executar script: {e}"
    
    # Se é bloqueante mas NÃO está configurado corretamente
    if is_blocking and not (has_nohup and has_background and has_pid_save):
        return (
            f"⚠️ AVISO: Este script pode travar o processo!\n\n"
            f"O script contém comandos de servidor ou processos de longa duração que vão bloquear a execução.\n\n"
            f"💡 SOLUÇÃO: Modifique o script para usar nohup em background e salvar o PID:\n"
            f"   nohup [comando] > output.log 2>&1 & echo $! > process.pid\n\n"
            f"📝 Exemplo de script corrigido:\n"
            f"   #!/bin/bash\n"
            f"   nohup uvicorn app:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &\n"
            f"   echo $! > server.pid\n"
            f"   echo \"Servidor iniciado com PID: $(cat server.pid)\"\n\n"
            f"🛑 Para parar depois:\n"
            f"   stop_background_process(\"server.pid\")"
        )
    
    try:
        result = subprocess.run([shell, '-c', script], cwd=str(workspace), capture_output=True, text=True, timeout=timeout)
        output = f"✓ Script {shell} executado\nExit code: {result.returncode}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        return output
    except subprocess.TimeoutExpired:
        return (
            f"✗ TIMEOUT: Script excedeu {timeout}s de execução.\n\n"
            f"⚠️ Este script pode conter processos de longa duração.\n"
            f"Se contiver servidores, modifique para usar nohup em background e salvar PID."
        )
    except FileNotFoundError:
        return f"✗ Shell não encontrado: {shell}"
    except Exception as e:
        return f"✗ Erro ao executar script: {e}"

@tool(
    description="""Para um processo que foi iniciado em background e teve seu PID salvo em arquivo.
Use esta ferramenta para parar servidores ou processos de longa duração que foram iniciados com nohup.
O arquivo PID deve ter sido criado anteriormente (ex: echo $! > server.pid).""",
    parameters={
        "pid_file": {"type": "string", "description": "Caminho do arquivo que contém o PID do processo (ex: 'server.pid', 'process.pid')"}
    },
    required=["pid_file"],
    complexity="simple"
)
def stop_background_process(pid_file: str, workspace: Path) -> str:
    """Para um processo em background usando arquivo PID."""
    try:
        pid_path = workspace / pid_file
        
        if not pid_path.exists():
            return f"✗ Arquivo PID não encontrado: {pid_file}"
        
        # Lê o PID
        with open(pid_path, 'r') as f:
            pid = f.read().strip()
        
        if not pid.isdigit():
            return f"✗ PID inválido no arquivo: {pid}"
        
        pid_int = int(pid)
        
        # Verifica se o processo existe
        try:
            os.kill(pid_int, 0)  # Signal 0 apenas verifica se o processo existe
        except ProcessLookupError:
            # Processo não existe mais
            pid_path.unlink()  # Remove o arquivo PID
            return f"ℹ️ Processo {pid_int} não existe mais. Arquivo PID removido."
        except PermissionError:
            return f"✗ Sem permissão para acessar o processo {pid_int}"
        
        # Tenta parar o processo graciosamente primeiro
        try:
            os.kill(pid_int, signal.SIGTERM)
            
            # Espera um pouco para ver se o processo termina
            time.sleep(2)
            
            # Verifica se ainda está rodando
            try:
                os.kill(pid_int, 0)
                # Ainda está rodando, força o kill
                os.kill(pid_int, signal.SIGKILL)
                time.sleep(1)
            except ProcessLookupError:
                pass  # Processo terminou
            
            # Remove o arquivo PID
            pid_path.unlink()
            
            return f"✓ Processo {pid_int} parado com sucesso. Arquivo {pid_file} removido."
            
        except ProcessLookupError:
            # Processo já terminou
            pid_path.unlink()
            return f"✓ Processo {pid_int} já havia terminado. Arquivo {pid_file} removido."
        except Exception as e:
            return f"✗ Erro ao parar processo {pid_int}: {e}"
            
    except Exception as e:
        return f"✗ Erro ao processar arquivo PID: {e}"
