import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.task import CreateTaskRequest, TaskOutputFile, TaskResponse
from app.services.task_service import TaskService
from app.workers.task_runner import run_task_background

router = APIRouter()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),  # noqa: B008
) -> TaskResponse:
    try:
        task = TaskService.create(
            db,
            tool_type=payload.tool_type,
            input_file_ids=payload.input_file_ids,
            params=payload.params,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # Schedule background execution
    background_tasks.add_task(run_task_background, task.id)

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        tool_type=task.tool_type.value,
        progress=task.progress,
        error_code=None,
        error_message=None,
        warnings=[],
        output_files=[],
        created_at=task.created_at,
        started_at=None,
        finished_at=None,
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),  # noqa: B008
) -> TaskResponse:
    task = TaskService.get(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    output_file_ids: list[int] = json.loads(task.output_file_ids) if task.output_file_ids else []
    raw_warnings = task.warnings
    warnings_list: list[str] = json.loads(raw_warnings) if raw_warnings else []

    output_files = [
        TaskOutputFile(
            file_id=fid,
            download_url=f"/api/files/{fid}/download",
            filename=f"output_{fid}",
        )
        for fid in output_file_ids
    ]

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        tool_type=task.tool_type.value,
        progress=task.progress,
        error_code=task.error_code,
        error_message=task.error_message,
        warnings=warnings_list,
        output_files=output_files,
        created_at=task.created_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
    )


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    db: Session = Depends(get_db),  # noqa: B008
    limit: int = 50,
    offset: int = 0,
) -> list[TaskResponse]:
    tasks = TaskService.list_by_user(db, limit=limit, offset=offset)
    result: list[TaskResponse] = []
    for task in tasks:
        raw_ids = task.output_file_ids
        output_file_ids: list[int] = json.loads(raw_ids) if raw_ids else []
        raw_warnings = task.warnings
        warnings_list: list[str] = json.loads(raw_warnings) if raw_warnings else []
        output_files = [
            TaskOutputFile(
                file_id=fid,
                download_url=f"/api/files/{fid}/download",
                filename=f"output_{fid}",
            )
            for fid in output_file_ids
        ]
        result.append(
            TaskResponse(
                task_id=task.id,
                status=task.status.value,
                tool_type=task.tool_type.value,
                progress=task.progress,
                error_code=task.error_code,
                error_message=task.error_message,
                warnings=warnings_list,
                output_files=output_files,
                created_at=task.created_at,
                started_at=task.started_at,
                finished_at=task.finished_at,
            )
        )
    return result


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    task = TaskService.get(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    TaskService.delete(db, task)
