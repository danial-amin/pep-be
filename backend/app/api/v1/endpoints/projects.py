"""
Project management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.deps import get_current_user, get_study_project_id
from app.models.user import User
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest, ProjectResponse
from app.services.project_service import ProjectService

router = APIRouter()


def _forbid_if_no_access(project, user: User, study_project_id: Optional[int] = None) -> None:
    if ProjectService.user_can_access(project, user.id, user.is_admin):
        return
    if study_project_id is not None and project.id == study_project_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this project",
    )


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new project owned by the current user."""
    try:
        project = await ProjectService.create_project(
            session=db,
            name=request.name,
            field_of_study=request.field_of_study,
            core_objective=request.core_objective,
            includes_context=request.includes_context,
            includes_interviews=request.includes_interviews,
            user_id=user.id,
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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    study_project_id: Optional[int] = Depends(get_study_project_id),
):
    """List projects for the current user (admins see all).

    Study participants also see their study's linked project.
    """
    projects = await ProjectService.get_all_projects(
        db, user_id=user.id, is_admin=user.is_admin
    )
    if study_project_id is not None and not user.is_admin:
        if not any(p.id == study_project_id for p in projects):
            linked = await ProjectService.get_project(db, study_project_id)
            if linked:
                projects = list(projects) + [linked]
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    study_project_id: Optional[int] = Depends(get_study_project_id),
):
    """Get a specific project by ID."""
    project = await ProjectService.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    _forbid_if_no_access(project, user, study_project_id)
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    request: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a project."""
    existing = await ProjectService.get_project(db, project_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    _forbid_if_no_access(existing, user)

    project = await ProjectService.update_project(
        session=db,
        project_id=project_id,
        name=request.name,
        field_of_study=request.field_of_study,
        core_objective=request.core_objective,
        includes_context=request.includes_context,
        includes_interviews=request.includes_interviews
    )
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a project and all associated data."""
    existing = await ProjectService.get_project(db, project_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    _forbid_if_no_access(existing, user)

    success = await ProjectService.delete_project(db, project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    await db.commit()
