"""
Project management service.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.models.project import Project
from app.models.document import Document
from app.models.persona import PersonaSet
import logging

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for project management."""
    
    @staticmethod
    async def create_project(
        session: AsyncSession,
        name: str,
        field_of_study: Optional[str] = None,
        core_objective: Optional[str] = None,
        includes_context: bool = True,
        includes_interviews: bool = True
    ) -> Project:
        """Create a new project."""
        project = Project(
            name=name,
            field_of_study=field_of_study,
            core_objective=core_objective,
            includes_context=includes_context,
            includes_interviews=includes_interviews
        )
        session.add(project)
        await session.flush()
        await session.refresh(project)
        return project
    
    @staticmethod
    async def get_project(
        session: AsyncSession,
        project_id: int
    ) -> Optional[Project]:
        """Get a project by ID."""
        result = await session.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_projects(
        session: AsyncSession
    ) -> List[Project]:
        """Get all projects."""
        result = await session.execute(select(Project).order_by(Project.created_at.desc()))
        return list(result.scalars().all())
    
    @staticmethod
    async def update_project(
        session: AsyncSession,
        project_id: int,
        name: Optional[str] = None,
        field_of_study: Optional[str] = None,
        core_objective: Optional[str] = None,
        includes_context: Optional[bool] = None,
        includes_interviews: Optional[bool] = None
    ) -> Optional[Project]:
        """Update a project."""
        project = await ProjectService.get_project(session, project_id)
        if not project:
            return None
        
        if name is not None:
            project.name = name
        if field_of_study is not None:
            project.field_of_study = field_of_study
        if core_objective is not None:
            project.core_objective = core_objective
        if includes_context is not None:
            project.includes_context = includes_context
        if includes_interviews is not None:
            project.includes_interviews = includes_interviews
        
        await session.flush()
        await session.refresh(project)
        return project
    
    @staticmethod
    async def delete_project(
        session: AsyncSession,
        project_id: int
    ) -> bool:
        """Delete a project and all associated data."""
        project = await ProjectService.get_project(session, project_id)
        if not project:
            return False
        
        # Delete all documents in the project
        result = await session.execute(
            select(Document).where(Document.project_id == str(project_id))
        )
        documents = result.scalars().all()
        for doc in documents:
            await session.delete(doc)
        
        # Delete all persona sets in the project
        result = await session.execute(
            select(PersonaSet).where(PersonaSet.project_id == project_id)
        )
        persona_sets = result.scalars().all()
        for ps in persona_sets:
            await session.delete(ps)
        
        # Delete the project
        await session.delete(project)
        await session.flush()
        return True
    
    @staticmethod
    async def get_project_documents(
        session: AsyncSession,
        project_id: int
    ) -> List[Document]:
        """Get all documents for a project."""
        result = await session.execute(
            select(Document).where(Document.project_id == str(project_id))
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_project_persona_sets(
        session: AsyncSession,
        project_id: int
    ) -> List[PersonaSet]:
        """Get all persona sets for a project."""
        result = await session.execute(
            select(PersonaSet).where(PersonaSet.project_id == project_id)
        )
        return list(result.scalars().all())
