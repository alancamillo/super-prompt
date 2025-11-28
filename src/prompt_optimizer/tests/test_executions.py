"""Testes para endpoints de execuções."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_execution(client: AsyncClient):
    """Testa criação de execução."""
    response = await client.post(
        "/api/v1/executions",
        json={
            "prompt_rendered": "Olá João, como posso ajudar?",
            "llm_response": "Olá! Estou aqui para ajudar.",
            "llm_model": "gpt-4o",
            "tokens_input": 15,
            "tokens_output": 8,
            "latency_ms": 250,
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["prompt_rendered"] == "Olá João, como posso ajudar?"
    assert data["llm_model"] == "gpt-4o"
    assert data["tokens_input"] == 15


@pytest.mark.asyncio
async def test_get_execution(client: AsyncClient):
    """Testa busca de execução por ID."""
    # Cria execução
    create_response = await client.post(
        "/api/v1/executions",
        json={
            "prompt_rendered": "Teste de busca",
            "llm_response": "Resposta teste",
            "llm_model": "gpt-4o-mini",
        },
    )
    execution_id = create_response.json()["id"]
    
    # Busca por ID
    response = await client.get(f"/api/v1/executions/{execution_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == execution_id


@pytest.mark.asyncio
async def test_list_executions(client: AsyncClient):
    """Testa listagem de execuções."""
    # Cria algumas execuções
    for i in range(3):
        await client.post(
            "/api/v1/executions",
            json={
                "prompt_rendered": f"Prompt {i}",
                "llm_response": f"Resposta {i}",
            },
        )
    
    response = await client.get("/api/v1/executions")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_update_execution(client: AsyncClient):
    """Testa atualização de execução."""
    # Cria execução sem resposta
    create_response = await client.post(
        "/api/v1/executions",
        json={
            "prompt_rendered": "Prompt para atualizar",
        },
    )
    execution_id = create_response.json()["id"]
    
    # Atualiza com resposta do LLM
    response = await client.patch(
        f"/api/v1/executions/{execution_id}",
        json={
            "llm_response": "Resposta adicionada depois",
            "llm_model": "claude-3-opus",
            "tokens_input": 50,
            "tokens_output": 100,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["llm_response"] == "Resposta adicionada depois"
    assert data["llm_model"] == "claude-3-opus"


@pytest.mark.asyncio
async def test_execution_not_found(client: AsyncClient):
    """Testa erro 404 para execução inexistente."""
    response = await client.get(
        "/api/v1/executions/00000000-0000-0000-0000-000000000000"
    )
    
    assert response.status_code == 404

