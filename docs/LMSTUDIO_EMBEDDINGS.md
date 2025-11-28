# Configuração do LM Studio para Embeddings

Este guia explica como configurar o LM Studio para gerar embeddings localmente, integrando com o Weaviate do Prompt Optimizer.

## Pré-requisitos

1. [LM Studio](https://lmstudio.ai/) instalado
2. Modelo de embeddings baixado

## Modelos de Embeddings Recomendados

| Modelo | Dimensões | Uso Recomendado |
|--------|-----------|-----------------|
| `nomic-ai/nomic-embed-text-v1.5` | 768 | Uso geral, bom balanço |
| `BAAI/bge-small-en-v1.5` | 384 | Rápido, menor consumo |
| `BAAI/bge-base-en-v1.5` | 768 | Melhor qualidade |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Clássico, bem testado |

## Passo a Passo

### 1. Baixar Modelo de Embeddings no LM Studio

```bash
# Via CLI (se disponível)
lms get nomic-ai/nomic-embed-text-v1.5

# Ou via interface gráfica:
# 1. Abra o LM Studio
# 2. Vá em "Discover" ou "Search"
# 3. Busque por "nomic-embed-text" ou "bge"
# 4. Clique em "Download"
```

### 2. Iniciar o Servidor de Embeddings

No LM Studio:

1. Vá para a aba **"Local Server"** (ícone de servidor)
2. Selecione o modelo de embeddings baixado
3. Clique em **"Start Server"**
4. O servidor iniciará em `http://localhost:1234`

**Importante:** O servidor deve estar rodando ANTES de iniciar o Prompt Optimizer.

### 3. Verificar se o Servidor está Funcionando

```bash
# Teste o endpoint de embeddings
curl http://localhost:1234/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Teste de embedding",
    "model": "nomic-embed-text-v1.5"
  }'
```

Resposta esperada:
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [0.123, -0.456, ...],
      "index": 0
    }
  ],
  "model": "nomic-embed-text-v1.5",
  "usage": {
    "prompt_tokens": 4,
    "total_tokens": 4
  }
}
```

### 4. Configurar o Prompt Optimizer

Edite o arquivo `.env`:

```env
# LM Studio local
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_EMBEDDING_MODEL=nomic-embed-text-v1.5
USE_LOCAL_EMBEDDINGS=true
```

Ou se rodando em Docker, use `host.docker.internal`:

```env
LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1
```

### 5. Iniciar o Prompt Optimizer

```bash
# Sem Docker
uvicorn src.prompt_optimizer.main:app --reload

# Com Docker
cd docker
docker compose up -d
```

## Configuração Alternativa: LM Studio em Outra Máquina

Se o LM Studio está rodando em outra máquina da rede:

```env
# Exemplo: LM Studio em 192.168.1.100
LMSTUDIO_BASE_URL=http://192.168.1.100:1234/v1
```

Certifique-se de que:
1. O firewall permite conexões na porta 1234
2. O LM Studio está configurado para aceitar conexões externas

## Fallback para OpenAI

Se quiser usar OpenAI como fallback ou alternativa:

```env
USE_LOCAL_EMBEDDINGS=false
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
```

## Troubleshooting

### Erro: "Connection refused"

- Verifique se o LM Studio está rodando
- Verifique se o servidor está iniciado (não apenas o modelo carregado)
- Verifique a URL e porta

### Erro: "Model not found"

- Certifique-se de que o nome do modelo em `LMSTUDIO_EMBEDDING_MODEL` corresponde exatamente ao modelo carregado no LM Studio

### Embeddings muito lentos

- Considere usar um modelo menor (ex: `bge-small-en-v1.5`)
- Verifique se sua GPU está sendo utilizada (se disponível)

### Docker não consegue acessar LM Studio

- Use `host.docker.internal` como host
- Adicione `extra_hosts: ["host.docker.internal:host-gateway"]` ao docker-compose
- Em Linux, pode ser necessário usar o IP real da máquina host

## Referências

- [LM Studio Docs - Embeddings](https://lmstudio.ai/docs/python/embedding)
- [Weaviate + LM Studio Forum](https://forum.weaviate.io/t/how-to-use-weaviate-with-lm-studio/3136)
- [Weaviate text2vec-openai](https://weaviate.io/developers/weaviate/model-providers/openai)

