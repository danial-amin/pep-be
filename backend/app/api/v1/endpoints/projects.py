"""
Project management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest, ProjectResponse
from app.services.project_service import ProjectService

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    try:
        project = await ProjectService.create_project(
            session=db,
            name=request.name,
            field_of_study=request.field_of_study,
            core_objective=request.core_objective,
            includes_context=request.includes_context,
            includes_interviews=request.includes_interviews
        )
        await db.commit()
        return ProjectResponse.model_validate(project)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating project: {str(e)}"
        )


@router.get("/", response_model=List[ProjectResponse])
async def get_all_projects(
    db: AsyncSession = Depends(get_db)
):
    """Get all projects."""
    projects = await ProjectService.get_all_projects(db)
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific project by ID."""
    project = await ProjectService.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    request: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a project."""
    project = await ProjectService.update_project(
        session=db,
        project_id=project_id,
        name=request.name,
        field_of_study=request.field_of_study,
        core_objective=request.core_objective,
        includes_context=request.includes_context,
        includes_interviews=request.includes_interviews
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a project and all associated data."""
    success = await ProjectService.delete_project(db, project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    await db.commit()
