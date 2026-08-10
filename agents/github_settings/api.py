from pathlib import Path
from typing import Any, Optional

import requests


class GitHubApiError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, token: str, api_url: str = 'https://api.github.com'):
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update(
            {
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {token}',
                'User-Agent': 'agents-github-settings',
                'X-GitHub-Api-Version': '2026-03-10',
            }
        )

    def get(self, path: str) -> Any:
        return self._request('GET', path)

    def patch(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request('PATCH', path, payload)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request('POST', path, payload)

    def put(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request('PUT', path, payload)

    def _request(
        self, method: str, path: str, payload: Optional[dict[str, Any]] = None
    ) -> Any:
        try:
            response = self.session.request(
                method,
                f'{self.api_url}{path}',
                json=payload,
                timeout=30,
            )
        except requests.RequestException as error:
            raise GitHubApiError(
                f'GitHub API {method} {path} failed: {error}'
            ) from error

        return self._decode(response)

    @staticmethod
    def _decode(response: requests.Response) -> Any:
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            raise GitHubApiError(
                f'GitHub API {response.request.method} {response.request.path_url} failed with '
                f'{response.status_code}: {response.text}'
            ) from error

        if not response.content:
            return None

        try:
            return response.json()
        except requests.JSONDecodeError as error:
            raise GitHubApiError(
                f'GitHub API returned invalid JSON for {response.request.method} {response.request.path_url}'
            ) from error


def write_output(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f'{path} already exists; pass --force to replace it')

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
