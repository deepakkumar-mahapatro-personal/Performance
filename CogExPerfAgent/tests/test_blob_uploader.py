from unittest.mock import MagicMock, patch

import pytest

from app.blob_uploader import (
    BlobUploadError,
    upload_execution_results,
)


def test_upload_execution_results(
    tmp_path,
    monkeypatch,
) -> None:
    execution_id = "test-execution-123"
    execution_directory = tmp_path / execution_id

    raw_file = (
        execution_directory
        / "raw"
        / "result.json"
    )
    report_file = (
        execution_directory
        / "reports"
        / "report.html"
    )

    raw_file.parent.mkdir(parents=True)
    report_file.parent.mkdir(parents=True)

    raw_file.write_text(
        '{"status": "ok"}',
        encoding="utf-8",
    )
    report_file.write_text(
        "<html>report</html>",
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "AZURE_STORAGE_CONNECTION_STRING",
        "test-connection-string",
    )
    monkeypatch.setenv(
        "AZURE_STORAGE_CONTAINER",
        "test-results",
    )

    with patch(
        "app.blob_uploader."
        "BlobServiceClient.from_connection_string"
    ) as create_client:
        service_client = MagicMock()
        container_client = MagicMock()

        create_client.return_value = service_client
        service_client.get_container_client.return_value = (
            container_client
        )

        uploaded_count = upload_execution_results(
            execution_directory=execution_directory,
            execution_id=execution_id,
        )

    assert uploaded_count == 2

    uploaded_names = {
        call.kwargs["name"]
        for call in container_client.upload_blob.call_args_list
    }

    assert uploaded_names == {
        f"{execution_id}/raw/result.json",
        f"{execution_id}/reports/report.html",
    }

    service_client.close.assert_called_once()


def test_missing_connection_string(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "AZURE_STORAGE_CONNECTION_STRING",
        raising=False,
    )
    monkeypatch.setenv(
        "AZURE_STORAGE_CONTAINER",
        "test-results",
    )

    with pytest.raises(
        BlobUploadError,
        match="AZURE_STORAGE_CONNECTION_STRING",
    ):
        upload_execution_results(
            execution_directory=tmp_path,
            execution_id="test-execution",
        )