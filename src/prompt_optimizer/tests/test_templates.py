"""Testes para endpoints de templates."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_template(client: AsyncClient):
    """Testa criação de template."""
    response = await client.post(
        "/api/v1/prompts/templates",
        json={
            "name": "test_template",
            "content": "Olá {{nome}}, como posso ajudar?",
            "metadata": {"author": "test"},
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test_template"
    assert data["version"] == 1
    assert data["is_active"] is True
    assert "{{nome}}" in data["content"]


@pytest.mark.asyncio
async def test_create_template_new_version(client: AsyncClient):
    """Testa criação de nova versão de template."""
    # Cria primeira versão
    response1 = await client.post(
        "/api/v1/prompts/templates",
        json={
            "name": "versioned_template",
            "content": "Versão 1",
            "metadata": {},
        },
    )
    assert response1.status_code == 201
    
    # Cria segunda versão
    response2 = await client.post(
        "/api/v1/prompts/templates",
        json={
            "name": "versioned_template",
            "content": "Versão 2",
            "metadata": {},
        },
    )
    assert response2.status_code == 201
    data = response2.json()
    assert data["version"] == 2
    assert data["content"] == "Versão 2"


@pytest.mark.asyncio
async def test_list_templates(client: AsyncClient):
    """Testa listagem de templates."""
    # Cria alguns templates
    for i in range(3):
        await client.post(
            "/api/v1/prompts/templates",
            json={
                "name": f"list_template_{i}",
                "content": f"Template {i}",
                "metadata": {},
            },
        )
    
    response = await client.get("/api/v1/prompts/templates")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3


@pytest.mark.asyncio
async def test_get_template_by_id(client: AsyncClient):
    """Testa busca de template por ID."""
    # Cria template
    create_response = await client.post(
        "/api/v1/prompts/templates",
        json={
            "name": "get_by_id_template",
            "content": "Conteúdo de teste",
            "metadata": {},
        },
    )
    template_id = create_response.json()["id"]
    
    # Busca por ID
    response = await client.get(f"/api/v1/prompts/templates/{template_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == template_id
    assert data["name"] == "get_by_id_template"


@pytest.mark.asyncio
async def test_get_template_by_name(client: AsyncClient):
    """Testa busca de template por nome."""
    # Cria template
    await client.post(
        "/api/v1/prompts/templates",
        json={
            "name": "named_template",
            "content": "Busca por nome",
            "metadata": {},
        },
    )
    
    # Busca por nome
    response = await client.get("/api/v1/prompts/templates/name/named_template")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "named_template"


@pytest.mark.asyncio
async def test_update_template(client: AsyncClient):
    """Testa atualização de template."""
    # Cria template
    create_response = await client.post(
        "/api/v1/prompts/templates",
        json={
            "name": "update_template",
            "content": "Conteúdo original",
            "metadata": {},
        },
    )
    template_id = create_response.json()["id"]
    
    # Atualiza
    response = await client.patch(
        f"/api/v1/prompts/templates/{template_id}",
        json={"content": "Conteúdo atualizado"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Conteúdo atualizado"


@pytest.mark.asyncio
async def test_deactivate_template(client: AsyncClient):
    """Testa desativação de template."""
    # Cria template
    create_response = await client.post(
        "/api/v1/prompts/templates",
        json={
            "name": "deactivate_template",
            "content": "Para desativar",
            "metadata": {},
        },
    )
    template_id = create_response.json()["id"]
    
    # Desativa
    response = await client.delete(f"/api/v1/prompts/templates/{template_id}")
    
    assert response.status_code == 204
    
    # Verifica que foi desativado
    get_response = await client.get(f"/api/v1/prompts/templates/{template_id}")
    assert get_response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_template_not_found(client: AsyncClient):
    """Testa erro 404 para template inexistente."""
    response = await client.get(
        "/api/v1/prompts/templates/00000000-0000-0000-0000-000000000000"
    )
    
    assert response.status_code == 404

