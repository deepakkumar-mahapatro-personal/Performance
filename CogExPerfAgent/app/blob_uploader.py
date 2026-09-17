import mimetypes
import os
from pathlib import Path

from azure.storage.blob import BlobServiceClient, ContentSettings


class BlobUploadError(RuntimeError):
    """Raised when execution results cannot be uploaded."""


def upload_execution_results(
    execution_directory: Path,
    execution_id: str,
) -> int:
    connection_string = os.getenv(
        "AZURE_STORAGE_CONNECTION_STRING"
    )
    container_name = os.getenv(
        "AZURE_STORAGE_CONTAINER"
    )

    if not connection_string:
        raise BlobUploadError(
            "AZURE_STORAGE_CONNECTION_STRING is not defined."
        )

    if not container_name:
        raise BlobUploadError(
            "AZURE_STORAGE_CONTAINER is not defined."
        )

    if not execution_directory.is_dir():
        raise BlobUploadError(
            f"Execution directory does not exist: "
            f"{execution_directory}"
        )

    files = sorted(
        path
        for path in execution_directory.rglob("*")
        if path.is_file()
    )

    if not files:
        raise BlobUploadError(
            f"No result files found in: {execution_directory}"
        )

    blob_service_client = (
        BlobServiceClient.from_connection_string(
            connection_string
        )
    )

    try:
        container_client = (
            blob_service_client.get_container_client(
                container_name
            )
        )

        for file_path in files:
            relative_path = file_path.relative_to(
                execution_directory
            )
            blob_name = (
                f"{execution_id}/"
                f"{relative_path.as_posix()}"
            )

            content_type, _ = mimetypes.guess_type(
                file_path.name
            )

            with file_path.open("rb") as data:
                container_client.upload_blob(
                    name=blob_name,
                    data=data,
                    overwrite=True,
                    content_settings=ContentSettings(
                        content_type=(
                            content_type
                            or "application/octet-stream"
                        )
                    ),
                )

            print(
                f"Uploaded blob: "
                f"{container_name}/{blob_name}"
            )
    except Exception as exc:
        raise BlobUploadError(
            f"Failed to upload execution "
            f"'{execution_id}': {exc}"
        ) from exc
    finally:
        blob_service_client.close()

    return len(files)