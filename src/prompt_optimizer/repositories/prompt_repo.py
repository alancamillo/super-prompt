"""Repository para PromptTemplate."""

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.db_models import PromptTemplate
from ..models.schemas import PromptTemplateCreate, PromptTemplateUpdate


class PromptTemplateRepository:
    """Repository para operações com PromptTemplate."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, data: PromptTemplateCreate) -> PromptTemplate:
        """Cria um novo template de prompt."""
        # Verifica se já existe e qual a última versão
        existing = await self.get_latest_by_name(data.name)
        version = 1 if existing is None else existing.version + 1
        
        template = PromptTemplate(
            name=data.name,
            content=data.content,
            version=version,
            metadata_=data.metadata,
        )
        self.session.add(template)
        await self.session.flush()
        await self.session.refresh(template)
        return template
    
    async def get_by_id(self, template_id: UUID) -> Optional[PromptTemplate]:
        """Busca template por ID."""
        result = await self.session.execute(
            select(PromptTemplate).where(PromptTemplate.id == template_id)
        )
        return result.scalar_one_or_none()
    
    async def get_latest_by_name(self, name: str) -> Optional[PromptTemplate]:
        """Busca a versão mais recente de um template pelo nome."""
        result = await self.session.execute(
            select(PromptTemplate)
            .where(PromptTemplate.name == name)
            .where(PromptTemplate.is_active == True)
            .order_by(PromptTemplate.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_by_name_and_version(
        self, 
        name: str, 
        version: int
    ) -> Optional[PromptTemplate]:
        """Busca template por nome e versão específica."""
        result = await self.session.execute(
            select(PromptTemplate)
            .where(PromptTemplate.name == name)
            .where(PromptTemplate.version == version)
        )
        return result.scalar_one_or_none()
    
    async def get_all_versions(self, name: str) -> list[PromptTemplate]:
        """Lista todas as versões de um template."""
        result = await self.session.execute(
            select(PromptTemplate)
            .where(PromptTemplate.name == name)
            .order_by(PromptTemplate.version.desc())
        )
        return list(result.scalars().all())
    
    async def list_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        active_only: bool = True
    ) -> tuple[list[PromptTemplate], int]:
        """Lista todos os templates (versões mais recentes)."""
        # Subquery para pegar última versão de cada nome
        subquery = (
            select(
                PromptTemplate.name,
                func.max(PromptTemplate.version).label("max_version")
            )
            .group_by(PromptTemplate.name)
            .subquery()
        )
        
        # Query principal
        query = (
            select(PromptTemplate)
            .join(
                subquery,
                (PromptTemplate.name == subquery.c.name) &
                (PromptTemplate.version == subquery.c.max_version)
            )
        )
        
        if active_only:
            query = query.where(PromptTemplate.is_active == True)
        
        # Count total
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0
        
        # Paginate
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        
        return list(result.scalars().all()), total
    
    async def update(
        self, 
        template_id: UUID, 
        data: PromptTemplateUpdate
    ) -> Optional[PromptTemplate]:
        """Atualiza um template existente."""
        template = await self.get_by_id(template_id)
        if template is None:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "metadata":
                setattr(template, "metadata_", value)
            else:
                setattr(template, field, value)
        
        await self.session.flush()
        await self.session.refresh(template)
        return template
    
    async def deactivate(self, template_id: UUID) -> bool:
        """Desativa um template."""
        template = await self.get_by_id(template_id)
        if template is None:
            return False
        
        template.is_active = False
        await self.session.flush()
        return True
    
    async def create_new_version(
        self, 
        name: str, 
        content: str, 
        metadata: Optional[dict] = None
    ) -> PromptTemplate:
        """Cria uma nova versão de um template existente."""
        return await self.create(PromptTemplateCreate(
            name=name,
            content=content,
            metadata=metadata or {},
        ))

