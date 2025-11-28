"""Testes para endpoints de feedbacks."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_add_feedback(client: AsyncClient):
    """Testa adição de feedback a uma execução."""
    # Cria execução
    exec_response = await client.post(
        "/api/v1/executions",
        json={
            "prompt_rendered": "Prompt para feedback",
            "llm_response": "Resposta do LLM",
        },
    )
    execution_id = exec_response.json()["id"]
    
    # Adiciona feedback
    response = await client.post(
        f"/api/v1/feedbacks/executions/{execution_id}",
        json={
            "rating": 4,
            "observation": "Boa resposta, mas poderia ser mais detalhada",
            "feedback_type": "positive",
            "created_by": "supervisor_teste",
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["rating"] == 4
    assert data["feedback_type"] == "positive"
    assert data["execution_id"] == execution_id


@pytest.mark.asyncio
async def test_add_negative_feedback(client: AsyncClient):
    """Testa adição de feedback negativo com sugestão."""
    # Cria execução
    exec_response = await client.post(
        "/api/v1/executions",
        json={
            "prompt_rendered": "Prompt ruim",
            "llm_response": "Resposta inadequada",
        },
    )
    execution_id = exec_response.json()["id"]
    
    # Adiciona feedback negativo
    response = await client.post(
        f"/api/v1/feedbacks/executions/{execution_id}",
        json={
            "rating": 2,
            "observation": "A resposta foi muito genérica",
            "suggested_correction": "Adicionar contexto específico sobre o produto",
            "feedback_type": "negative",
            "created_by": "qa_team",
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["rating"] == 2
    assert data["feedback_type"] == "negative"
    assert "Adicionar contexto" in data["suggested_correction"]


@pytest.mark.asyncio
async def test_list_execution_feedbacks(client: AsyncClient):
    """Testa listagem de feedbacks de uma execução."""
    # Cria execução
    exec_response = await client.post(
        "/api/v1/executions",
        json={
            "prompt_rendered": "Prompt com múltiplos feedbacks",
            "llm_response": "Resposta",
        },
    )
    execution_id = exec_response.json()["id"]
    
    # Adiciona múltiplos feedbacks
    for i in range(3):
        await client.post(
            f"/api/v1/feedbacks/executions/{execution_id}",
            json={
                "rating": i + 1,
                "observation": f"Feedback {i}",
                "feedback_type": "suggestion",
            },
        )
    
    # Lista feedbacks
    response = await client.get(f"/api/v1/feedbacks/executions/{execution_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_list_pending_feedbacks(client: AsyncClient):
    """Testa listagem de feedbacks pendentes de revisão."""
    # Cria execução com feedback do tipo suggestion
    exec_response = await client.post(
        "/api/v1/executions",
        json={
            "prompt_rendered": "Prompt",
            "llm_response": "Resposta",
        },
    )
    execution_id = exec_response.json()["id"]
    
    await client.post(
        f"/api/v1/feedbacks/executions/{execution_id}",
        json={
            "observation": "Sugestão pendente",
            "feedback_type": "suggestion",
        },
    )
    
    # Lista pendentes
    response = await client.get("/api/v1/feedbacks/pending")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    # Todos devem ser do tipo suggestion
    for item in data["items"]:
        assert item["feedback_type"] == "suggestion"


@pytest.mark.asyncio
async def test_feedback_execution_not_found(client: AsyncClient):
    """Testa erro 404 ao adicionar feedback em execução inexistente."""
    response = await client.post(
        "/api/v1/feedbacks/executions/00000000-0000-0000-0000-000000000000",
        json={
            "rating": 3,
            "observation": "Teste",
            "feedback_type": "positive",
        },
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_invalid_feedback_type(client: AsyncClient):
    """Testa validação de tipo de feedback inválido."""
    # Cria execução
    exec_response = await client.post(
        "/api/v1/executions",
        json={
            "prompt_rendered": "Prompt",
            "llm_response": "Resposta",
        },
    )
    execution_id = exec_response.json()["id"]
    
    # Tenta criar feedback com tipo inválido
    response = await client.post(
        f"/api/v1/feedbacks/executions/{execution_id}",
        json={
            "rating": 3,
            "feedback_type": "invalid_type",
        },
    )
    
    assert response.status_code == 422  # Validation error

