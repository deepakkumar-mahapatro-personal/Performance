import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from app.blob_uploader import (
    BlobUploadError,
    upload_execution_results,
)
from app.main import get_output_directory

app = FastAPI(
    title="CogExPerfAgent API",
    version="0.1.0",
)


REQUIRED_CONFIG_FILES = (
    "application.yaml",
    "collector_types.yaml",
    "components.yaml",
    "entities.yaml",
    "reporting.yaml",
    "rules.yaml",
)
PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent

class RunRequest(BaseModel):
    entity: str = Field(
        min_length=1,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$",
    )
    start_time: datetime
    end_time: datetime
    interval: str | None = Field(
        default=None,
        pattern=r"^[1-9][0-9]*[smhd]$",
    )
    component: str | None = Field(
        default=None,
        min_length=1,
    )


class RunAcceptedResponse(BaseModel):
    execution_id: str
    status: Literal["queued"]


@app.get("/health")
def health() -> dict[str, str]:
    """
    Confirm that the API process is running.
    """

    return {
        "status": "healthy",
    }


@app.get("/ready")
def ready() -> JSONResponse:
    """
    Confirm that the required configuration files are readable.
    """

    config_directory = Path(
        os.getenv(
            "PERF_CONFIG_DIR",
            "config",
        )
    )

    missing_files = [
        filename
        for filename in REQUIRED_CONFIG_FILES
        if not (config_directory / filename).is_file()
    ]

    if missing_files:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "config_directory": str(config_directory),
                "missing_files": missing_files,
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "config_directory": str(config_directory),
        },
    )



def execute_perf_agent(
    run_request: RunRequest,
    execution_id: str,
) -> None:
    """
    Execute the existing command-line application.

    This background execution is intended for local API integration
    testing. Production status handling will be added later.
    """

    command = [
        sys.executable,
        "-m",
        "app.main",
        "--entity",
        run_request.entity,
        "--start-time",
        run_request.start_time.isoformat(),
        "--end-time",
        run_request.end_time.isoformat(),
        "--execution-id",
        execution_id,
    ]

    if run_request.interval:
        command.extend(
            [
                "--interval",
                run_request.interval,
            ]
        )

    if run_request.component:
        command.extend(
            [
                "--component",
                run_request.component,
            ]
        )

    print()
    print(f"Starting API execution: {execution_id}")
    print(f"Command: {' '.join(command)}")

    completed_process = subprocess.run(
        command,
        cwd=PROJECT_DIRECTORY,
        check=False,
    )

    print(
        f"Execution {execution_id} finished with "
        f"exit code {completed_process.returncode}"
    )
    if completed_process.returncode != 0:
        return

    output_directory = get_output_directory()

    if not output_directory.is_absolute():
        output_directory = (
            PROJECT_DIRECTORY / output_directory
        )

    execution_directory = (
        output_directory / execution_id
    )

    try:
        uploaded_file_count = (
            upload_execution_results(
                execution_directory=execution_directory,
                execution_id=execution_id,
            )
        )
    except BlobUploadError as exc:
        print(
            f"Blob upload failed for execution "
            f"{execution_id}: {exc}"
        )
        return

    print(
        f"Blob upload completed for execution "
        f"{execution_id}. Uploaded files: "
        f"{uploaded_file_count}"
    )

@app.post(
    "/runs",
    response_model=RunAcceptedResponse,
    status_code=202,
)

def create_run(
    run_request: RunRequest,
    background_tasks: BackgroundTasks,
) -> RunAcceptedResponse:
    """
    Validate and accept a performance-agent run.

    Execution will be connected in the next implementation step.
    """

    if (
        run_request.start_time.tzinfo is None
        or run_request.end_time.tzinfo is None
    ):
        raise HTTPException(
            status_code=422,
            detail="Start and end times must include a timezone.",
        )

    if run_request.start_time >= run_request.end_time:
        raise HTTPException(
            status_code=422,
            detail="Start time must be earlier than end time.",
        )

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    execution_id = (
        f"{run_request.entity}-"
        f"{timestamp}-"
        f"{uuid4().hex[:8]}"
    )

    background_tasks.add_task(
        execute_perf_agent,
        run_request,
        execution_id,
    )

    return RunAcceptedResponse(
        execution_id=execution_id,
        status="queued",
    )