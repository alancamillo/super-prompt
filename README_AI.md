# 🤖 AI Code Agent - Resumo Completo

## 🚀 NOVO: Suporte ao GPT-5! (2025)

O agente agora suporta os **novos modelos GPT-5** lançados pela OpenAI em agosto de 2025:

| Modelo | Custo ($/M tokens) | Uso Recomendado |
|--------|-------------------|-----------------|
| **gpt-5** | $1.25 in / $10 out | Tarefas complexas, raciocínio avançado |
| **gpt-5-mini** ⭐ | $0.25 in / $2 out | **Produção - melhor custo-benefício** |
| **gpt-5-nano** | $0.05 in / $0.40 out | Alto volume, tarefas simples |

```python
# Usando GPT-5-mini (recomendado)
agent = ModernAIAgent(model='gpt-5-mini')
agent.execute_task("Adicione testes para main.py")

# Ou GPT-5 completo para tarefas complexas
agent = ModernAIAgent(model='gpt-5', max_iterations=50)
agent.execute_task("Refatore código aplicando SOLID e DDD")
```

✅ **100% compatível** - Mesma API, sem mudanças no código!  
📚 [Demo completo](demo_gpt5.py) | [Documentação OpenAI](https://openai.com/gpt-5)

---

## 📚 O Que Foi Criado

Este projeto agora possui **3 versões de agentes de IA** para edição de código, cada uma com sua arquitetura e caso de uso:

### 1. **Modern AI Agent** ⭐ RECOMENDADO
- **Arquivo:** `modern_ai_agent.py`
- **Arquitetura:** ReAct (Reasoning + Acting) com OpenAI Function Calling nativo
- **Status:** ✅ Pronto para produção
- **Ferramentas:** 16 tools (arquivos, shell, validação, posicionamento inteligente)
- **Modelos:** GPT-5, GPT-5-mini, GPT-5-nano, GPT-4o, GPT-4o-mini
- **Melhor para:** Tarefas complexas, edições precisas, código bem organizado

### 2. **AI Code Agent**
- **Arquivo:** `ai_code_agent.py`
- **Arquitetura:** Funções específicas pré-definidas
- **Status:** ✅ Estável
- **Melhor para:** Tarefas específicas conhecidas

### 3. **LangChain Code Agent**
- **Arquivo:** `langchain_code_agent.py`
- **Arquitetura:** Agente conversacional simplificado
- **Status:** ⚠️  Experimental
- **Melhor para:** Aprendizado e experimentação

---

## 🚀 Início Rápido

### 1. Instale as Dependências

```bash
pip install -r requirements.txt
```

### 2. Configure a API Key

Adicione ao arquivo `.env`:

```bash
OPENAI_API_KEY=sk-sua_chave_aqui
```

### 3. Execute

```bash
# Modern AI Agent (Recomendado)
python modern_ai_agent.py

# AI Code Agent
python ai_code_agent.py

# Teste/Demo
python demo_ai_integration.py
```

---

## 💡 Exemplos de Uso

### Modern AI Agent (Recomendado)

```python
from modern_ai_agent import ModernAIAgent

# Inicializa
agent = ModernAIAgent()

# Uso simples - o agente decide o que fazer
agent.execute_task("Liste todos os arquivos Python no projeto")

agent.execute_task("""
Refatore o arquivo app.py:
1. Melhore nomes de variáveis
2. Adicione type hints
3. Adicione docstrings
""")

agent.execute_task("""
Crie um novo arquivo utils.py com funções para:
- Validar email
- Formatar CPF
- Calcular idade
""")

# 🆕 NOVO: Comandos Shell
agent.execute_task("Execute 'git status' e me diga o estado do repositório")

agent.execute_task("""
Execute um script que:
1. Conte arquivos Python
2. Mostre tamanho total do projeto
3. Verifique se há testes
""")

# Modo interativo
agent.chat()
```

### AI Code Agent

```python
from ai_code_agent import AICodeAgent

agent = AICodeAgent()

# Funções específicas
agent.analyze_code("app.py")
agent.suggest_refactoring("app.py")
agent.add_documentation_ai("app.py")
agent.fix_bugs_ai("app.py", bug_description="Função retorna None")
agent.generate_code_ai("Crie validador de CPF", "validator.py")
agent.explain_code_ai("app.py")
agent.chat_about_code("app.py")
```

---

## 📖 Documentação Completa

### Guias Disponíveis

1. **`AI_INTEGRATION_GUIDE.md`** - Guia completo de integração
   - Setup detalhado
   - Exemplos práticos
   - Troubleshooting
   - Comparações

2. **`AGENT_ARCHITECTURES.md`** ⭐ LEIA ESTE
   - Arquiteturas de agentes (ReAct, Plan-Execute, etc.)
   - Melhores práticas
   - Quando usar cada uma
   - Tendências 2025

3. **`SHELL_TOOLS_GUIDE.md`** 🆕 NOVO
   - Ferramentas de shell script
   - Exemplos de uso (git, CI/CD, análise)
   - Segurança e validações
   - Casos de uso avançados

4. **`QUICKSTART.md`** - Início rápido do Code Agent básico

5. **`README_CODE_AGENT.md`** - Documentação do Code Agent base

---

## 🏗️ Arquitetura

### Visão Geral

```
┌─────────────────────────────────────────┐
│         USUÁRIO                         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│      MODERN AI AGENT (Recomendado)       │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  OpenAI Function Calling           │ │
│  │  - gpt-4o-mini / gpt-4o            │ │
│  │  - ReAct pattern                   │ │
│  └────────────┬───────────────────────┘ │
│               │                          │
│               ▼                          │
│  ┌────────────────────────────────────┐ │
│  │  TOOLS (8 ferramentas)             │ │
│  │  - read_file                       │ │
│  │  - write_file                      │ │
│  │  - search_replace                  │ │
│  │  - edit_lines                      │ │
│  │  - list_files                      │ │
│  │  - show_file                       │ │
│  │  - run_command    🆕 NOVO          │ │
│  │  - run_script     🆕 NOVO          │ │
│  └────────────┬───────────────────────┘ │
│               │                          │
└───────────────┼──────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────┐
│         CODE AGENT (Base)                │
│  - Manipulação de arquivos               │
│  - Diffs e backups                       │
│  - Validações                            │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│         SISTEMA DE ARQUIVOS              │
│  - Leitura/Escrita                       │
│  - Backups (.code_agent_backups/)        │
└──────────────────────────────────────────┘
```

### Por que Modern AI Agent?

1. **Tecnologia Nativa** - Usa OpenAI Function Calling diretamente
2. **Sem Dependências Pesadas** - Não depende de LangChain
3. **Mais Confiável** - APIs estáveis da OpenAI
4. **Transparente** - Você vê cada tool call
5. **Pronto para Produção** - Testado e robusto

---

## 🎯 Casos de Uso

### 1. Refatoração Automática

```python
agent = ModernAIAgent()

agent.execute_task("""
Refatore todos os arquivos Python:
- Use type hints em todas as funções
- Adicione docstrings
- Renomeie variáveis de 1 letra
- Adicione tratamento de erros
""")
```

### 2. Análise de Código

```python
agent.execute_task("""
Analise o arquivo main.py e me diga:
1. O que o código faz
2. Problemas potenciais
3. Sugestões de melhoria
4. Nota de qualidade (1-10)
""")
```

### 3. Geração de Código

```python
agent.execute_task("""
Crie um arquivo database.py com:
- Classe DatabaseConnection usando context manager
- Métodos para CRUD básico
- Tratamento de erros SQLite
- Type hints e docstrings
""")
```

### 4. Migração de Código

```python
agent.execute_task("""
Migre o arquivo legacy.py de Python 2 para Python 3:
- print statements -> print()
- unicode() -> str()
- Divisão / para //
- Atualize imports
""")
```

### 5. Documentação Automática

```python
agent.execute_task("""
Adicione documentação completa a todos os arquivos .py:
- Docstrings no formato Google
- Comentários em lógica complexa
- README.md com overview do projeto
""")
```

### 6. Operações DevOps com Shell 🆕

```python
agent.execute_task("""
Execute pipeline de CI/CD:
1. Verifique git status
2. Execute testes com pytest
3. Verifique coverage
4. Se tudo passar, faça commit das mudanças
5. Gere relatório de build
""")
```

### 7. Análise de Projeto com Shell 🆕

```python
agent.execute_task("""
Analise o projeto completo:
1. Conte linhas de código por tipo (Python, JS, etc)
2. Encontre arquivos grandes (>100KB)
3. Liste dependências do requirements.txt
4. Verifique se há arquivos duplicados
5. Gere relatório de complexidade
""")
```

---

## 🔧 Customização

### Adicionar Nova Tool

```python
from modern_ai_agent import ModernAIAgent

agent = ModernAIAgent()

# Define a ferramenta
def my_custom_tool(param1: str, param2: int) -> str:
    """Sua lógica aqui"""
    return f"Processado: {param1} com {param2}"

# Registra
agent.register_tool(
    name="my_tool",
    description="Descrição clara do que a tool faz",
    parameters={
        "param1": {
            "type": "string",
            "description": "Descrição do parâmetro 1"
        },
        "param2": {
            "type": "integer",
            "description": "Descrição do parâmetro 2"
        }
    },
    required=["param1", "param2"],
    function=my_custom_tool
)

# Use
agent.execute_task("Use my_tool com os valores apropriados")
```

### Customizar Modelo

```python
# Mais rápido e barato (recomendado para teste)
agent = ModernAIAgent(model="gpt-4o-mini")

# Mais poderoso (melhor qualidade)
agent = ModernAIAgent(model="gpt-4o")

# Limitar iterações (segurança)
agent = ModernAIAgent(max_iterations=5)

# Modo silencioso
agent = ModernAIAgent(verbose=False)
```

---

## 📊 Comparação Rápida

| Feature | Modern AI | AI Code | LangChain |
|---------|-----------|---------|-----------|
| **Autonomia** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Controle** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Simplicidade** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Produção** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Flexibilidade** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 💰 Custos Estimados

Baseado em `gpt-4o-mini` (mais barato):

| Operação | Tokens | Custo (USD) |
|----------|--------|-------------|
| Listar arquivos | ~500 | $0.0003 |
| Ler + Analisar | ~2000 | $0.0012 |
| Refatorar arquivo | ~5000 | $0.003 |
| Projeto completo | ~50000 | $0.03 |

**gpt-4o** é ~10x mais caro mas ~2x melhor qualidade.

**Dica:** Use `gpt-4o-mini` para testes, `gpt-4o` para produção crítica.

---

## 🛡️ Segurança

### O que já está implementado:

- ✅ **Backups automáticos** - Todo arquivo editado gera backup
- ✅ **Validação de paths** - Não acessa fora do workspace
- ✅ **Limite de iterações** - Evita loops infinitos
- ✅ **Tratamento de erros** - Erros não quebram o agente
- ✅ **API Key em .env** - Não expõe credenciais

### Recomendações adicionais:

```python
# Use em sandbox/container
docker run -v $(pwd):/workspace python-ai-agent

# Limite permissões
chmod 755 workspace/

# Monitore custos
# Configure billing limits na OpenAI

# Revise mudanças
git diff  # Antes de commitar
```

---

## 🐛 Troubleshooting

### "OPENAI_API_KEY não encontrada"

```bash
echo "OPENAI_API_KEY=sk-..." > .env
```

### "Invalid API Key"

1. Verifique a chave em [platform.openai.com](https://platform.openai.com/api-keys)
2. Confirme que tem créditos
3. Teste com `curl`:

```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### "Rate limit exceeded"

- Você excedeu limites da OpenAI
- Espere alguns minutos ou upgrade o tier

### Agente faz loops

```python
# Reduza max_iterations
agent = ModernAIAgent(max_iterations=5)

# Ou seja mais específico na tarefa
agent.execute_task("Faça EXATAMENTE isto: ...")
```

---

## 📈 Métricas e Monitoramento

```python
# Após executar tarefa
result = agent.execute_task("Sua tarefa")

print(f"Sucesso: {result['success']}")
print(f"Iterações: {result['iterations']}")
print(f"Tool calls: {result['tool_calls']}")
print(f"Resposta: {result['response']}")
```

---

## 🎓 Próximos Passos

1. ✅ Leia `AGENT_ARCHITECTURES.md` para entender arquiteturas
2. ✅ Execute `python demo_ai_integration.py` para testar
3. ✅ Experimente `python modern_ai_agent.py`
4. ✅ Customize para seu caso de uso
5. ✅ Adicione suas próprias tools
6. ✅ Integre no seu workflow

---

## 📞 Suporte

### Documentação

- [OpenAI API Docs](https://platform.openai.com/docs)
- [Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)

### Arquivos Deste Projeto

```
.
├── modern_ai_agent.py          # ⭐ PRINCIPAL - Agente moderno
├── ai_code_agent.py            # Funções específicas
├── langchain_code_agent.py     # Experimental
├── code_agent.py               # Base (sem IA)
├── demo_ai_integration.py      # Script de demonstração
│
├── AGENT_ARCHITECTURES.md      # ⭐ Leia sobre arquiteturas
├── AI_INTEGRATION_GUIDE.md     # Guia completo de integração
├── README_AI.md                # Este arquivo
├── README_CODE_AGENT.md        # Docs do Code Agent base
└── QUICKSTART.md               # Início rápido
```

---

## ✨ Resumo Final

**Para começar AGORA:**

```bash
# 1. Instale
pip install -r requirements.txt

# 2. Configure
echo "OPENAI_API_KEY=sk-..." > .env

# 3. Execute
python modern_ai_agent.py
```

**Primeira tarefa sugerida:**

```python
from modern_ai_agent import ModernAIAgent

agent = ModernAIAgent()
agent.execute_task("Liste os arquivos Python neste projeto e analise um deles")
```

**Pronto! Você tem um agente de IA funcionando!** 🎉

---

**Desenvolvido com 🤖 IA e ❤️ Python**

*Arquitetura baseada em pesquisa e melhores práticas de 2025*

