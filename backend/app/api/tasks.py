import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import File
from app.schemas.task import (
    CreateTaskRequest,
    TaskInputFile,
    TaskListResponse,
    TaskOutputFile,
    TaskResponse,
)
from app.services.task_service import TaskService
from app.workers.task_runner import run_task_background


def _resolve_output_files(output_file_ids: list[int], db: Session) -> list[TaskOutputFile]:
    """Build TaskOutputFile list by looking up the File table for real filenames."""
    result: list[TaskOutputFile] = []
    for fid in output_file_ids:
        file_rec = db.query(File).filter(File.id == fid).first()
        filename = file_rec.original_name if file_rec else f"output_{fid}"
        result.append(
            TaskOutputFile(
                file_id=fid,
                download_url=f"/api/files/{fid}/download",
                filename=filename,
            )
        )
    return result

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

    raw_input_names: list[str] = json.loads(task.input_file_names) if task.input_file_names else []
    input_files = [
        TaskInputFile(file_id=fid, original_name=name)
        for fid, name in zip(payload.input_file_ids, raw_input_names)
    ]

    return TaskResponse(
        task_id=task.id,
        task_name=task.task_name,
        status=task.status.value,
        tool_type=task.tool_type.value,
        progress=task.progress,
        error_code=None,
        error_message=None,
        warnings=[],
        output_files=[],
        input_files=input_files,
        result_info={},
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

    output_files = _resolve_output_files(output_file_ids, db)

    # Parse input file names
    raw_input_ids: list[int] = json.loads(task.input_file_ids) if task.input_file_ids else []
    raw_input_names: list[str] = json.loads(task.input_file_names) if task.input_file_names else []
    input_files = [
        TaskInputFile(file_id=fid, original_name=name)
        for fid, name in zip(raw_input_ids, raw_input_names)
    ]

    return TaskResponse(
        task_id=task.id,
        task_name=task.task_name,
        status=task.status.value,
        tool_type=task.tool_type.value,
        progress=task.progress,
        error_code=task.error_code,
        error_message=task.error_message,
        warnings=warnings_list,
        output_files=output_files,
        input_files=input_files,
        result_info=task.result_info,
        created_at=task.created_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
    )


@router.get("", response_model=TaskListResponse)
def list_tasks(
    db: Session = Depends(get_db),  # noqa: B008
    limit: int = 30,
    offset: int = 0,
    task_name: str | None = None,
    file_name: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> TaskListResponse:
    tasks, total = TaskService.search_tasks(
        db,
        task_name=task_name,
        file_name=file_name,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    items: list[TaskResponse] = []
    for task in tasks:
        raw_ids = task.output_file_ids
        output_file_ids: list[int] = json.loads(raw_ids) if raw_ids else []
        raw_warnings = task.warnings
        warnings_list: list[str] = json.loads(raw_warnings) if raw_warnings else []
        raw_input_ids: list[int] = json.loads(task.input_file_ids) if task.input_file_ids else []
        raw_input_names: list[str] = json.loads(task.input_file_names) if task.input_file_names else []
        output_files = _resolve_output_files(output_file_ids, db)
        input_files = [
            TaskInputFile(file_id=fid, original_name=name)
            for fid, name in zip(raw_input_ids, raw_input_names)
        ]
        items.append(
            TaskResponse(
                task_id=task.id,
                task_name=task.task_name,
                status=task.status.value,
                tool_type=task.tool_type.value,
                progress=task.progress,
                error_code=task.error_code,
                error_message=task.error_message,
                warnings=warnings_list,
                output_files=output_files,
                input_files=input_files,
                result_info=task.result_info,
                created_at=task.created_at,
                started_at=task.started_at,
                finished_at=task.finished_at,
            )
        )
    return TaskListResponse(items=items, total=total)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_tasks(
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    """Delete all tasks."""
    TaskService.delete_all(db)


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
