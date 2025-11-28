"""Testes de integração do fluxo completo."""

import pytest
from httpx import AsyncClient

from ..services.embeddings import EmbeddingService


class TestCompleteFlow:
    """Testes do fluxo completo de otimização e feedback."""
    
    @pytest.mark.asyncio
    async def test_complete_optimization_flow(self, client: AsyncClient):
        """
        Testa fluxo completo:
        1. Cria template
        2. Otimiza prompt (skip - requer Weaviate)
        3. Registra execução
        4. Adiciona feedback
        """
        # 1. Cria template
        template_response = await client.post(
            "/api/v1/prompts/templates",
            json={
                "name": "vendedor_seguros",
                "content": """Você é {{nome_vendedor}}, um vendedor de seguros experiente.
Contexto do cliente: {{contexto_cliente}}
Responda de forma {{tom}} a seguinte pergunta: {{pergunta}}""",
                "metadata": {
                    "author": "test",
                    "domain": "seguros",
                },
            },
        )
        assert template_response.status_code == 201
        template = template_response.json()
        
        # 2. Registra execução (simulando uso do prompt)
        execution_response = await client.post(
            "/api/v1/executions",
            json={
                "prompt_template_id": template["id"],
                "prompt_rendered": """Você é João, um vendedor de seguros experiente.
Contexto do cliente: Cliente novo, primeira consulta
Responda de forma amigável a seguinte pergunta: Como faço para contratar um seguro de vida?""",
                "llm_response": """Olá! Que ótimo que você está pensando em proteger sua família!

O seguro de vida é uma excelente forma de garantir segurança financeira para quem você ama. 
Para contratar, precisamos avaliar alguns pontos:

1. Qual é sua idade e condição de saúde?
2. Quantas pessoas dependem de você financeiramente?
3. Qual cobertura você considera adequada?

Posso fazer uma simulação para você agora mesmo!""",
                "llm_model": "gpt-4o",
                "tokens_input": 89,
                "tokens_output": 156,
                "latency_ms": 850,
            },
        )
        assert execution_response.status_code == 201
        execution = execution_response.json()
        
        # 3. Adiciona feedback positivo
        feedback_response = await client.post(
            f"/api/v1/feedbacks/executions/{execution['id']}",
            json={
                "rating": 4,
                "observation": "Resposta boa, fez perguntas relevantes",
                "feedback_type": "positive",
                "created_by": "supervisor_maria",
            },
        )
        assert feedback_response.status_code == 201
        
        # 4. Adiciona sugestão de melhoria
        suggestion_response = await client.post(
            f"/api/v1/feedbacks/executions/{execution['id']}",
            json={
                "rating": 4,
                "observation": "Faltou mencionar opções de pagamento",
                "suggested_correction": "Adicionar ao prompt: 'Sempre mencione as opções de pagamento disponíveis'",
                "feedback_type": "suggestion",
                "created_by": "supervisor_maria",
            },
        )
        assert suggestion_response.status_code == 201
        
        # 5. Verifica que os feedbacks foram registrados
        feedbacks_response = await client.get(
            f"/api/v1/feedbacks/executions/{execution['id']}"
        )
        assert feedbacks_response.status_code == 200
        feedbacks = feedbacks_response.json()
        assert len(feedbacks) == 2
    
    @pytest.mark.asyncio
    async def test_template_versioning_flow(self, client: AsyncClient):
        """Testa fluxo de versionamento de templates."""
        # Cria versão 1
        v1_response = await client.post(
            "/api/v1/prompts/templates",
            json={
                "name": "versioned_prompt",
                "content": "Versão original do prompt: {{pergunta}}",
                "metadata": {"version_notes": "Versão inicial"},
            },
        )
        assert v1_response.status_code == 201
        v1 = v1_response.json()
        assert v1["version"] == 1
        
        # Cria versão 2 com melhorias
        v2_response = await client.post(
            "/api/v1/prompts/templates",
            json={
                "name": "versioned_prompt",
                "content": "Versão melhorada do prompt com contexto: {{contexto}}\nPergunta: {{pergunta}}",
                "metadata": {"version_notes": "Adicionado campo de contexto"},
            },
        )
        assert v2_response.status_code == 201
        v2 = v2_response.json()
        assert v2["version"] == 2
        
        # Busca por nome retorna versão mais recente
        latest_response = await client.get(
            "/api/v1/prompts/templates/name/versioned_prompt"
        )
        assert latest_response.status_code == 200
        latest = latest_response.json()
        assert latest["version"] == 2
        
        # Pode buscar versão específica
        v1_specific = await client.get(
            "/api/v1/prompts/templates/name/versioned_prompt?version=1"
        )
        assert v1_specific.status_code == 200
        assert v1_specific.json()["version"] == 1
        
        # Lista todas as versões
        versions_response = await client.get(
            f"/api/v1/prompts/templates/{v1['id']}/versions"
        )
        assert versions_response.status_code == 200
        versions = versions_response.json()
        assert len(versions) == 2
    
    @pytest.mark.asyncio
    async def test_feedback_aggregation_flow(self, client: AsyncClient):
        """Testa agregação de feedbacks para análise."""
        # Cria múltiplas execuções com feedbacks variados
        for i in range(5):
            exec_response = await client.post(
                "/api/v1/executions",
                json={
                    "prompt_rendered": f"Prompt {i}",
                    "llm_response": f"Resposta {i}",
                    "llm_model": "gpt-4o",
                    "tokens_input": 50 + i * 10,
                    "tokens_output": 100 + i * 20,
                },
            )
            execution = exec_response.json()
            
            # Adiciona feedbacks variados
            feedback_type = ["positive", "negative", "suggestion"][i % 3]
            rating = (i % 5) + 1
            
            await client.post(
                f"/api/v1/feedbacks/executions/{execution['id']}",
                json={
                    "rating": rating,
                    "observation": f"Observação {i}",
                    "feedback_type": feedback_type,
                    "created_by": f"user_{i}",
                },
            )
        
        # Verifica resumo de feedbacks
        summary_response = await client.get("/api/v1/analytics/feedback-summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["total_feedbacks"] >= 5
        assert summary["positive_count"] >= 1
        assert summary["negative_count"] >= 1


class TestEmbeddingService:
    """Testes para o serviço de embeddings."""
    
    def test_generate_hash_consistency(self):
        """Testa que hashes são consistentes."""
        service = EmbeddingService()
        
        text = "Como faço para contratar um seguro de vida?"
        hash1 = service.generate_hash(text)
        hash2 = service.generate_hash(text)
        
        assert hash1 == hash2
    
    def test_generate_hash_normalization(self):
        """Testa normalização de texto para hash."""
        service = EmbeddingService()
        
        # Textos equivalentes após normalização
        text1 = "Como faço para contratar um seguro?"
        text2 = "COMO FAÇO PARA CONTRATAR UM SEGURO?"
        text3 = "como   faço  para   contratar  um  seguro?"
        
        hash1 = service.generate_hash(text1)
        hash2 = service.generate_hash(text2)
        hash3 = service.generate_hash(text3)
        
        assert hash1 == hash2 == hash3
    
    def test_generate_cache_key(self):
        """Testa geração de chave de cache."""
        service = EmbeddingService()
        
        key1 = service.generate_cache_key("Como contratar seguro?")
        key2 = service.generate_cache_key("Como contratar seguro?", "vendedor_seguros")
        
        assert key1 != key2
        assert "vendedor_seguros:" in key2

