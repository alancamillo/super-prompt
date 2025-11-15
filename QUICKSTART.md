# 🚀 Guia de Início Rápido - AI Code Agent

## Instalação em 3 passos

```bash
# 1. Clone ou navegue até o diretório
cd /caminho/do/projeto

# 2. Instale a dependência
pip install rich

# 3. Pronto para usar!
python code_agent.py
```

## 💡 Uso Básico

### Modo Interativo (Recomendado para iniciantes)

```bash
python code_agent.py
```

Isso abrirá um menu com opções numeradas. Navegue facilmente pelas funcionalidades!

### Modo Programático (Para automação)

```python
from code_agent import CodeAgent

# Inicializa
agent = CodeAgent()

# Operações básicas
content = agent.read_file("meu_arquivo.py")
agent.write_file("novo.py", "print('Hello!')", show_preview=True)
agent.search_replace("meu_arquivo.py", "old", "new")
```

## 🎯 Casos de Uso Principais

### 1. Edição Rápida com Preview

```python
agent = CodeAgent()

# Edita e mostra diff antes de aplicar
agent.edit_lines(
    "app.py",
    start_line=10,
    end_line=15,
    new_content="# Novo código aqui\nprint('Updated!')"
)
# Usuário aprova/rejeita após ver o diff colorido
```

### 2. Múltiplas Edições Seguras

```python
from code_agent import CodeAgent, FileEdit

agent = CodeAgent()

# Define múltiplas edições (ordem qualquer!)
edits = [
    FileEdit(5, 5, "# Comentário linha 5", "Adiciona comentário"),
    FileEdit(20, 22, "# Substitui 3 linhas", "Refatora código"),
    FileEdit(50, 50, "print('fim')", "Adiciona print"),
]

# Aplica todas de uma vez (ordem reversa automática!)
agent.apply_edits("arquivo.py", edits)
```

### 3. Refatoração em Lote

```python
agent = CodeAgent()

# Renomeia função em todos os arquivos
import pathlib

for arquivo in pathlib.Path(".").glob("*.py"):
    agent.search_replace(
        str(arquivo),
        "funcao_antiga",
        "funcao_nova",
        show_preview=True
    )
```

## ⚠️ Dica Importante: Múltiplas Edições

Quando fizer edições que adicionam/removem linhas:

### ❌ ERRADO - Índices desatualizados
```python
agent.edit_lines("app.py", 5, 5, "nova linha")  # +1 linha
agent.edit_lines("app.py", 15, 15, "outra")     # Linha 15 agora é 16!
```

### ✅ CORRETO - Use apply_edits()
```python
edits = [
    FileEdit(5, 5, "nova linha", "Edit 1"),
    FileEdit(15, 15, "outra", "Edit 2"),  # Índice original OK!
]
agent.apply_edits("app.py", edits)  # Ordem reversa automática
```

## 🧪 Testar Instalação

```bash
# Teste rápido
python test_code_agent.py

# Exemplos práticos
python example_usage.py
```

## 📖 Exemplos Incluídos

O arquivo `example_usage.py` contém 6 exemplos práticos:

1. **Refatoração de variáveis** - Renomeia variáveis para nomes mais descritivos
2. **Adicionar documentação** - Adiciona docstrings e type hints
3. **Tratamento de erros** - Adiciona try/except em funções
4. **Refatoração para OOP** - Converte código procedural em classes
5. **Edições múltiplas complexas** - Melhora API Flask com várias edições
6. **Migração Python 2→3** - Atualiza sintaxe antiga

Execute:
```bash
python example_usage.py
```

## 🛡️ Segurança

✅ **Backups automáticos** - Todo arquivo editado gera backup em `.code_agent_backups/`
✅ **Preview obrigatório** - Veja diffs coloridos antes de aplicar
✅ **Confirmação do usuário** - Aprove ou rejeite cada mudança
✅ **Validação de índices** - Detecta índices de linha inválidos

## 📁 Estrutura de Arquivos

```
.
├── code_agent.py              # ← Código principal
├── test_code_agent.py         # ← Suite de testes
├── example_usage.py           # ← 6 exemplos práticos
├── requirements.txt           # ← Dependências
├── README_CODE_AGENT.md       # ← Documentação completa
├── QUICKSTART.md              # ← Este arquivo
└── .code_agent_backups/       # ← Backups (criado automaticamente)
```

## 🎨 Interface Visual

O Code Agent usa `rich` para criar uma interface linda:

- 🎨 Syntax highlighting automático
- 📊 Diffs coloridos (verde=adicionado, vermelho=removido)
- 📋 Tabelas formatadas
- ✅ Confirmações interativas
- 📦 Painéis e bordas elegantes

## 🤔 Precisa de Ajuda?

### Problema: "ModuleNotFoundError: No module named 'rich'"
**Solução:**
```bash
pip install rich
```

### Problema: "Arquivo não encontrado"
**Solução:** Use caminhos relativos ao workspace ou absolutos
```python
agent = CodeAgent(workspace="/caminho/do/projeto")
```

### Problema: Backups ocupando espaço
**Solução:** Backups ficam em `.code_agent_backups/` - pode deletar os antigos
```bash
rm -rf .code_agent_backups/*.backup
```

### Problema: "Linha está além do arquivo"
**Solução:** Use `agent.show_file()` para ver quantas linhas o arquivo tem
```python
agent.show_file("meu_arquivo.py")
# Veja o número da última linha no display
```

## 🚀 Próximos Passos

1. ✅ Execute `python code_agent.py` para modo interativo
2. ✅ Explore `python example_usage.py` para ver casos reais
3. ✅ Rode `python test_code_agent.py` para validar
4. ✅ Leia `README_CODE_AGENT.md` para documentação completa
5. ✅ Integre no seu fluxo de trabalho!

---

**Desenvolvido com ❤️ e Python**

Pronto para editar código como um profissional! 🎉

