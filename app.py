from src.super_prompt.modern_ai_agent import ModernAIAgent
from src.super_prompt.config import AgentConfig

# Configure and initialize the agent using the AgentConfig model
config = AgentConfig(
    simple_model="gpt-4o-mini",
    complex_model="gpt-4o",
    use_multi_model=True,
    log_file="logs/agent_session.log"
)
agent = ModernAIAgent(config=config)

# Uso simples - o agente decide o que fazer
# agent.execute_task("""crie uma aplicaçao simples usando fastapi de nome main2.py. Que tenham os seguintes metodos: 
# uppercase_nome(nome: str) -> str: que recebe um nome e retorna o mesmo em uppercase. e lowercase_nome(nome: str) -> str: 
# que recebe um nome e retorna o mesmo em lowercase.""")

agent.execute_task("crie e teste uma aplicaçao simples usando fastapi de nome main.py. adicione e instale dependencias via requirements.txt")

# agent.execute_task("""
# adicione um metodo http GET que recebe um parametro 'nome' 
# e retorna o mesmo em uppercase (main.py).
# """)

# agent.execute_task("""
# chame o metodo uppercase_nome(nome) da aplicação main.py usando curl shell. 
# (verifique se a aplicação esta rodando e nao, execute em background com nohup antes de realizar a chamada. Desligue a aplicação apos a chamada.)
# nome: "joao"
# resultado: "JOAO"
# """)
# agent.execute_task("""
# no arquivo main.py, antes de dar upper acrescente a palavra "_TESTE" como sufixo no nome passado como parametro.
# """)
# agent.execute_task("""
# no arquivo main.py, apique teste pytest para o metodo uppercase_nome.
# """)

# agent.execute_task("""
# no arquivo tests/test_main.py, adicione sys.path.append(str(Path(__file__).resolve().parents[1])) para que o arquivo main.py seja encontrado pelo pytest.
# """)

# agent.execute_task("""
# crie um arquivo do tipo .md com o nome prompt1.md e adicione 
# um prompt de um vende dor de seguros chamado joao.
# """)

# agent.execute_task("""
# crie prompt2.md baseado em prompt1.md porém com foco na pergunta do usuário. 
# O objetivo é tornarmos o prompt1 mais aderente a pergunta do usuário. 
# Porém mantendo o contexto do prompt1 e as orientaçoes essenciais.
# Pergunta do usuário: "como faço para contratar um seguro de vida?"
# """)
# agent.execute_task("""
# crie prompt3.md baseado em prompt1.md porém com foco na pergunta do usuário. 
# O objetivo é tornarmos o prompt1 mais aderente a pergunta do usuário. 
# Porém mantendo o contexto do prompt1 e as orientaçoes essenciais.
# Pergunta do usuário: "Voce é uma IA?"
# """)