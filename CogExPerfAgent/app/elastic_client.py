import os
from typing import Any

import requests
from requests import Response, Session
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    RequestException,
    Timeout,
)


class ElasticClientError(Exception):
    """Raised when communication with Elasticsearch fails."""


class ElasticClient:
    """
    Generic HTTP client for Elasticsearch.

    Responsibilities:
        - Manage authentication.
        - Send HTTP requests.
        - Handle SSL and timeout configuration.
        - Convert Elasticsearch responses into Python dictionaries.

    This class does not build Elasticsearch queries.
    """

    def __init__(
        self,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        auth_type: str = "basic",
        timeout_seconds: int = 60,
        verify_ssl: bool = True,
        ca_certificate: str | None = None,
    ) -> None:
        if not base_url or not base_url.strip():
            raise ElasticClientError(
                "Elasticsearch URL is missing."
            )

        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

        # requests accepts either:
        #   True/False
        #   or a path to a CA certificate file.
        self.verify: bool | str = (
            ca_certificate
            if ca_certificate
            else verify_ssl
        )

        self.session = Session()

        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        self._configure_authentication(
            auth_type=auth_type,
            username=username,
            password=password,
            api_key=api_key,
        )

    @classmethod
    def from_config(
        cls,
        elastic_config: dict[str, Any],
    ) -> "ElasticClient":
        """
        Create an ElasticClient using application.yaml and environment variables.

        application.yaml supplies:
            - URL
            - authentication type
            - timeout
            - SSL settings

        Environment variables supply:
            - username/password
            - or API key
        """

        auth_type = str(
            elastic_config.get("auth_type", "basic")
        ).lower()

        return cls(
            base_url=str(elastic_config.get("url", "")),
            username=os.getenv("ELASTIC_USERNAME"),
            password=os.getenv("ELASTIC_PASSWORD"),
            api_key=os.getenv("ELASTIC_API_KEY"),
            auth_type=auth_type,
            timeout_seconds=int(
                elastic_config.get("timeout_seconds", 60)
            ),
            verify_ssl=bool(
                elastic_config.get("verify_ssl", True)
            ),
            ca_certificate=elastic_config.get(
                "ca_certificate"
            ),
        )

    def _configure_authentication(
        self,
        auth_type: str,
        username: str | None,
        password: str | None,
        api_key: str | None,
    ) -> None:
        """
        Configure authentication for the HTTP session.

        Supported authentication types:
            - basic
            - api_key
            - none
        """

        if auth_type == "basic":
            if not username or not password:
                raise ElasticClientError(
                    "ELASTIC_USERNAME and ELASTIC_PASSWORD "
                    "must be defined for basic authentication."
                )

            self.session.auth = (username, password)
            return

        if auth_type == "api_key":
            if not api_key:
                raise ElasticClientError(
                    "ELASTIC_API_KEY must be defined "
                    "for API-key authentication."
                )

            self.session.headers.update(
                {
                    "Authorization": f"ApiKey {api_key}"
                }
            )
            return

        if auth_type == "none":
            return

        raise ElasticClientError(
            f"Unsupported Elasticsearch authentication type: "
            f"{auth_type}"
        )

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send an HTTP request to Elasticsearch.
        """

        normalized_path = path.lstrip("/")
        url = f"{self.base_url}/{normalized_path}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=body,
                params=params,
                timeout=self.timeout_seconds,
                verify=self.verify,
            )

        except Timeout as exc:
            raise ElasticClientError(
                f"Elasticsearch request timed out after "
                f"{self.timeout_seconds} seconds: {url}"
            ) from exc

        except RequestsConnectionError as exc:
            raise ElasticClientError(
                f"Could not connect to Elasticsearch: {url}. "
                f"Check the URL, DNS, network access and proxy settings."
            ) from exc

        except RequestException as exc:
            raise ElasticClientError(
                f"Elasticsearch request failed: {exc}"
            ) from exc

        self._validate_response(response)

        if response.status_code == 204 or not response.content:
            return {}

        try:
            result = response.json()
        except ValueError as exc:
            raise ElasticClientError(
                "Elasticsearch returned a non-JSON response. "
                f"HTTP status: {response.status_code}"
            ) from exc

        if not isinstance(result, dict):
            raise ElasticClientError(
                "Expected an Elasticsearch JSON object response."
            )

        return result

    @staticmethod
    def _validate_response(response: Response) -> None:
        """
        Convert unsuccessful HTTP responses into readable errors.
        """

        if response.ok:
            return

        try:
            error_body: Any = response.json()
        except ValueError:
            error_body = response.text

        # Prevent extremely large HTML/error responses from
        # filling the terminal.
        error_text = str(error_body)[:2000]

        raise ElasticClientError(
            f"Elasticsearch returned HTTP "
            f"{response.status_code}: {error_text}"
        )

    def get_cluster_info(self) -> dict[str, Any]:
        """
        Test connectivity and retrieve basic Elasticsearch information.
        """

        return self._request(
            method="GET",
            path="/",
        )

    def search(
        self,
        index: str,
        query: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a synchronous Elasticsearch search request.
        """

        if not index or not index.strip():
            raise ElasticClientError(
                "Elasticsearch index cannot be empty."
            )

        if not isinstance(query, dict):
            raise ElasticClientError(
                "Elasticsearch query must be a dictionary."
            )

        return self._request(
            method="POST",
            path=f"/{index}/_search",
            body=query,
            params=params,
        )

    def close(self) -> None:
        """Close the HTTP session."""

        self.session.close()

    def __enter__(self) -> "ElasticClient":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self.close()