import json
import threading
import webbrowser
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import quote, unquote, urlparse

from agent_flow.config import WorkflowConfigError, load_workflow_snapshot, workflow_snapshot
from agent_flow.store import RUNS_DIRECTORY, RunStore, RunStoreError


class ViewerError(RuntimeError):
    pass


def serve_viewer(
    repository_root: Path,
    *,
    run_id: Optional[str] = None,
    port: int = 0,
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
    port: int = 0,
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
        server_version = 'AgentFlow'
        sys_version = ''

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == '/':
                self._send_bytes(_viewer_html(), 'text/html; charset=utf-8')
                return
            if parsed.path == '/api/runs':
                self._send_json({'repository_root': str(repository_root), 'runs': _list_runs(repository_root)})
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
            if parsed.path == '/favicon.ico':
                self._send_bytes(b'', 'image/x-icon', status=HTTPStatus.NO_CONTENT)
                return
            self._send_json({'error': 'Not found'}, status=HTTPStatus.NOT_FOUND)

        def do_HEAD(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == '/':
                self._send_bytes(_viewer_html(), 'text/html; charset=utf-8', include_body=False)
                return
            self._send_json({'error': 'Not found'}, status=HTTPStatus.NOT_FOUND, include_body=False)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_json(
            self,
            value: dict,
            *,
            status: HTTPStatus = HTTPStatus.OK,
            include_body: bool = True,
        ) -> None:
            self._send_bytes(
                json.dumps(value, separators=(',', ':')).encode('utf-8'),
                'application/json; charset=utf-8',
                status=status,
                include_body=include_body,
            )

        def _send_bytes(
            self,
            content: bytes,
            content_type: str,
            *,
            status: HTTPStatus = HTTPStatus.OK,
            include_body: bool = True,
        ) -> None:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header(
                'Content-Security-Policy',
                "default-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; "
                "style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'",
            )
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            if include_body:
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
    if not runs_directory.resolve().is_relative_to(repository_root):
        return []

    try:
        paths = list(runs_directory.iterdir())
    except OSError:
        return []

    runs = []
    for path in paths:
        if not path.is_dir():
            continue
        try:
            store = RunStore.open(repository_root, path.name)
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
        workflow = workflow_snapshot(load_workflow_snapshot(store.workflow_path))
    except WorkflowConfigError as error:
        raise RunStoreError(f'Cannot read workflow snapshot {store.workflow_path}: {error}') from error

    events = []
    warnings = []
    if store.events_path.is_symlink():
        warnings.append('Ignored unsafe events.jsonl symlink')
    elif store.events_path.is_file():
        try:
            with store.events_path.open('r', encoding='utf-8', errors='replace') as event_file:
                lines = deque(enumerate(event_file, start=1), maxlen=200)
            for line_number, line in lines:
                if line.strip():
                    try:
                        event = json.loads(line)
                        if not isinstance(event, dict):
                            raise ValueError
                        events.append(event)
                    except (json.JSONDecodeError, ValueError):
                        warnings.append(f'Ignored malformed event at events.jsonl:{line_number}')
        except OSError as error:
            raise RunStoreError(f'Cannot read run events {store.events_path}: {error}') from error

    artifacts = []
    excluded = {store.state_path, store.workflow_path, store.events_path, store.lock_path}
    for path in store.run_directory.rglob('*'):
        if not path.is_file() or path in excluded:
            continue
        if path.is_symlink():
            warnings.append(f'Ignored unsafe run file symlink: {path.relative_to(store.run_directory)}')
            continue
        try:
            stat = path.stat()
        except OSError:
            warnings.append(f'Ignored unreadable run file: {path.relative_to(store.run_directory)}')
            continue
        artifacts.append(
            {
                'path': str(path.relative_to(store.run_directory)),
                'size': stat.st_size,
                'updated_at': stat.st_mtime,
            }
        )
        if len(artifacts) == 1000:
            warnings.append('Showing the first 1,000 run files')
            break

    return {
        'state': state.to_dict(),
        'workflow': workflow,
        'events': events,
        'artifacts': sorted(artifacts, key=lambda item: item['path']),
        'warnings': warnings,
    }
