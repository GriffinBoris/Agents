import json
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import quote, unquote, urlparse

from agent_flow.store import RUNS_DIRECTORY, RunStore, RunStoreError


class ViewerError(RuntimeError):
    pass


def serve_viewer(
    repository_root: Path,
    *,
    run_id: Optional[str] = None,
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    server = create_viewer_server(repository_root, run_id=run_id, port=port)
    actual_port = server.server_address[1]
    query = f'?run={quote(run_id)}' if run_id is not None else ''
    url = f'http://127.0.0.1:{actual_port}/{query}'
    print(f'Agent Flow viewer: {url}', flush=True)
    print('Press Ctrl-C to stop.', flush=True)

    if open_browser:
        threading.Timer(0.1, webbrowser.open, args=(url,)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def create_viewer_server(
    repository_root: Path,
    *,
    run_id: Optional[str] = None,
    port: int = 8765,
) -> ThreadingHTTPServer:
    root = repository_root.resolve()
    if not root.is_dir():
        raise ViewerError(f'Repository root does not exist: {root}')
    if not 0 <= port <= 65535:
        raise ViewerError('Viewer port must be between 0 and 65535')
    if run_id is not None:
        try:
            RunStore.open(root, run_id)
        except RunStoreError as error:
            raise ViewerError(str(error)) from error

    handler = _handler_for(root)
    try:
        return ThreadingHTTPServer(('127.0.0.1', port), handler)
    except OSError as error:
        raise ViewerError(f'Cannot start viewer on port {port}: {error}') from error


def _handler_for(repository_root: Path) -> type[BaseHTTPRequestHandler]:
    class ViewerHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == '/':
                self._send_bytes(_viewer_html(), 'text/html; charset=utf-8')
                return
            if parsed.path == '/api/runs':
                self._send_json({'runs': _list_runs(repository_root)})
                return
            if parsed.path.startswith('/api/runs/'):
                run_id = unquote(parsed.path.removeprefix('/api/runs/'))
                try:
                    payload = _load_run(repository_root, run_id)
                except RunStoreError as error:
                    self._send_json({'error': str(error)}, status=HTTPStatus.NOT_FOUND)
                    return
                self._send_json(payload)
                return
            self._send_json({'error': 'Not found'}, status=HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_json(self, value: dict, *, status: HTTPStatus = HTTPStatus.OK) -> None:
            self._send_bytes(
                json.dumps(value, separators=(',', ':')).encode('utf-8'),
                'application/json; charset=utf-8',
                status=status,
            )

        def _send_bytes(
            self,
            content: bytes,
            content_type: str,
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header(
                'Content-Security-Policy',
                "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'",
            )
            self.end_headers()
            self.wfile.write(content)

    return ViewerHandler


def _viewer_html() -> bytes:
    try:
        return Path(__file__).with_name('viewer.html').read_bytes()
    except OSError as error:
        raise ViewerError(f'Cannot load bundled viewer: {error}') from error


def _list_runs(repository_root: Path) -> list[dict]:
    runs_directory = repository_root / RUNS_DIRECTORY
    if not runs_directory.is_dir():
        return []

    runs = []
    for path in runs_directory.iterdir():
        if not path.is_dir():
            continue
        store = RunStore(path)
        try:
            state = store.load_state()
        except RunStoreError:
            continue
        runs.append(
            {
                'run_id': state.run_id,
                'workflow_name': state.workflow_name,
                'status': state.status,
                'current_step': state.current_step,
                'created_at': state.created_at,
                'updated_at': state.updated_at,
            }
        )
    return sorted(runs, key=lambda item: item['updated_at'], reverse=True)


def _load_run(repository_root: Path, run_id: str) -> dict:
    store = RunStore.open(repository_root, run_id)
    state = store.load_state()
    try:
        workflow = json.loads(store.workflow_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as error:
        raise RunStoreError(f'Cannot read workflow snapshot {store.workflow_path}: {error}') from error

    events = []
    if store.events_path.is_file():
        try:
            lines = store.events_path.read_text(encoding='utf-8').splitlines()
            for line in lines[-200:]:
                if line.strip():
                    events.append(json.loads(line))
        except (json.JSONDecodeError, OSError) as error:
            raise RunStoreError(f'Cannot read run events {store.events_path}: {error}') from error

    artifacts = []
    excluded = {store.state_path, store.workflow_path, store.events_path}
    for path in store.run_directory.rglob('*'):
        if not path.is_file() or path in excluded:
            continue
        stat = path.stat()
        artifacts.append(
            {
                'path': str(path.relative_to(store.run_directory)),
                'size': stat.st_size,
                'updated_at': stat.st_mtime,
            }
        )

    return {
        'state': state.to_dict(),
        'workflow': workflow,
        'events': events,
        'artifacts': sorted(artifacts, key=lambda item: item['path']),
    }
