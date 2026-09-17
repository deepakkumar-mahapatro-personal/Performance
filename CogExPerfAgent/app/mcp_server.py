import csv
from pathlib import Path
from typing import Optional
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("CogExPerfAgent")


@mcp.tool()
def test_connection(message: str = "Hello") -> dict:
    """Verify that GitHub Copilot can call CogExPerfAgent through MCP."""
    return {
        "status": "success",
        "application": "CogExPerfAgent",
        "received_message": message,
    }


from pathlib import Path


@mcp.tool()
def list_executions(limit: int = 20) -> dict:
    """List available CogExPerfAgent execution folders from the output directory."""

    output_directory = Path.cwd() / "output"

    if not output_directory.exists():
        return {
            "status": "error",
            "message": f"Output directory not found: {output_directory}",
            "executions": [],
        }

    executions = [
        {
            "execution_id": path.name,
            "last_modified": path.stat().st_mtime,
        }
        for path in output_directory.iterdir()
        if path.is_dir()
    ]

    executions.sort(
        key=lambda execution: execution["last_modified"],
        reverse=True,
    )

    return {
        "status": "success",
        "total_found": len(executions),
        "returned": min(len(executions), limit),
        "executions": [
            execution["execution_id"]
            for execution in executions[:limit]
        ],
    }

@mcp.tool()
def get_execution_summary(
    execution_id: str,
    entity: Optional[str] = None,
) -> dict:
    """
    Read the aggregated entity summary for a CogExPerfAgent execution.

    If entity is not provided, summaries for every entity under the
    execution are returned.
    """

    # Prevent paths such as ../../config/.env
    if Path(execution_id).name != execution_id:
        return {
            "status": "error",
            "message": "Invalid execution_id",
        }

    output_directory = Path.cwd() / "output"
    execution_directory = output_directory / execution_id
    aggregated_directory = execution_directory / "aggregated"

    if not execution_directory.is_dir():
        return {
            "status": "error",
            "message": f"Execution not found: {execution_id}",
        }

    if not aggregated_directory.is_dir():
        return {
            "status": "error",
            "message": f"Aggregated results not found for: {execution_id}",
        }

    if entity:
        if Path(entity).name != entity:
            return {
                "status": "error",
                "message": "Invalid entity",
            }

        summary_files = [
            aggregated_directory / entity / "entity-summary.csv"
        ]
    else:
        summary_files = sorted(
            aggregated_directory.glob("*/entity-summary.csv")
        )

    summaries = []

    for summary_file in summary_files:
        if not summary_file.is_file():
            continue

        with summary_file.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            rows = list(csv.DictReader(csv_file))

        summaries.append(
            {
                "entity": summary_file.parent.name,
                "source_file": str(
                    summary_file.relative_to(Path.cwd())
                ),
                "metrics": rows,
            }
        )

    if not summaries:
        return {
            "status": "error",
            "execution_id": execution_id,
            "message": "No entity-summary.csv files found",
        }

    return {
        "status": "success",
        "execution_id": execution_id,
        "entities_found": len(summaries),
        "summaries": summaries,
    }

@mcp.tool()
def generate_entity_result(
    entity: str,
    start_time: str,
    end_time: str,
    interval: str = "30s",
) -> dict:
    """
    Generate CogExPerfAgent results for an entity and time range.

    Use this tool when the user asks to collect, generate, build or create
    a performance result. Times must use ISO-8601 format, preferably UTC,
    for example: 2026-07-27T14:42:15.755Z.
    """

    # Prevent unsafe entity values from becoming command arguments or paths.
    if not re.fullmatch(r"[A-Za-z0-9._-]+", entity):
        return {
            "status": "error",
            "message": "Invalid entity name",
        }

    # Accept intervals such as 30s, 1m or 1h.
    if not re.fullmatch(r"[1-9][0-9]*[smh]", interval):
        return {
            "status": "error",
            "message": (
                "Invalid interval. Use values such as 30s, 1m or 1h."
            ),
        }

    try:
        parsed_start = datetime.fromisoformat(
            start_time.replace("Z", "+00:00")
        )
        parsed_end = datetime.fromisoformat(
            end_time.replace("Z", "+00:00")
        )
    except ValueError:
        return {
            "status": "error",
            "message": (
                "Invalid time format. Use ISO-8601, for example "
                "2026-07-27T14:42:15.755Z."
            ),
        }

    if parsed_start >= parsed_end:
        return {
            "status": "error",
            "message": "start_time must be earlier than end_time",
        }

    project_directory = Path.cwd()
    output_directory = project_directory / "output"

    existing_executions = {
        path.name
        for path in output_directory.iterdir()
        if path.is_dir()
    } if output_directory.exists() else set()

    command = [
        sys.executable,
        "-m",
        "app.main",
        "--entity",
        entity,
        "--start-time",
        start_time,
        "--end-time",
        end_time,
        "--interval",
        interval,
    ]

    try:
        completed_process = subprocess.run(
            command,
            cwd=project_directory,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "entity": entity,
            "message": "Result generation exceeded the 30-minute timeout",
        }
    except Exception as exception:
        return {
            "status": "error",
            "entity": entity,
            "message": f"Unable to start result generation: {exception}",
        }

    current_executions = {
        path.name
        for path in output_directory.iterdir()
        if path.is_dir()
    } if output_directory.exists() else set()

    generated_executions = sorted(
        current_executions - existing_executions
    )

    if completed_process.returncode != 0:
        return {
            "status": "error",
            "entity": entity,
            "return_code": completed_process.returncode,
            "message": "CogExPerfAgent result generation failed",
            "stderr": completed_process.stderr[-5000:],
            "stdout": completed_process.stdout[-5000:],
        }

    return {
        "status": "success",
        "entity": entity,
        "start_time": start_time,
        "end_time": end_time,
        "interval": interval,
        "generated_executions": generated_executions,
        "stdout": completed_process.stdout[-5000:],
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")