"""Minimal stdio LSP client for pyright-langserver."""

import json
import subprocess
from pathlib import Path
import shutil


class PyrightLspClient:
    """Minimal stdio JSON-RPC client for pyright-langserver.

    Implements only the LSP features needed for references:
    - initialize / initialized
    - textDocument/didOpen
    - textDocument/references
    - shutdown / exit
    """

    def __init__(self, server_cmd=None):
        self.server_cmd = server_cmd or ["pyright-langserver", "--stdio"]
        self.proc = None
        self._next_id = 1
        self._started = False

    def start(self, repo_root: str):
        """Start the LSP server and initialize."""
        if self._started:
            return
        executable = self.server_cmd[0]
        if shutil.which(executable) is None:
            raise RuntimeError(f"LSP server executable '{executable}' not found in PATH.")

        self.proc = subprocess.Popen(
            self.server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.request(
            "initialize",
            {
                "processId": None,
                "rootUri": Path(repo_root).resolve().as_uri(),
                "capabilities": {},
                "workspaceFolders": [
                    {
                        "name": Path(repo_root).name,
                        "uri": Path(repo_root).resolve().as_uri(),
                    }
                ],
            },
        )
        self.notify("initialized", {})
        self._started = True

    def _write_message(self, payload: dict):
        """Write a JSON-RPC message to stdin."""
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        assert self.proc and self.proc.stdin
        self.proc.stdin.write(header + body)
        self.proc.stdin.flush()

    def _read_message(self) -> dict:
        """Read a JSON-RPC message from stdout."""
        assert self.proc and self.proc.stdout
        headers = b""
        while b"\r\n\r\n" not in headers:
            chunk = self.proc.stdout.read(1)
            if not chunk:
                raise RuntimeError("LSP server closed stdout unexpectedly")
            headers += chunk

        header_blob, _ = headers.split(b"\r\n\r\n", 1)
        content_length = None
        for line in header_blob.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                content_length = int(line.split(b":", 1)[1].strip())
                break
        if content_length is None:
            raise RuntimeError("Missing Content-Length header")

        body = self.proc.stdout.read(content_length)
        return json.loads(body.decode("utf-8"))

    def request(self, method: str, params: dict):
        """Send a request and wait for response."""
        msg_id = self._next_id
        self._next_id += 1
        self._write_message(
            {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}
        )

        while True:
            message = self._read_message()
            if message.get("id") == msg_id:
                if "error" in message:
                    raise RuntimeError(f"LSP error for {method}: {message['error']}")
                return message.get("result")

    def notify(self, method: str, params: dict):
        """Send a notification (no response)."""
        self._write_message({"jsonrpc": "2.0", "method": method, "params": params})

    def did_open(self, uri: str, text: str):
        """Send textDocument/didOpen notification."""
        self.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": "python",
                    "version": 1,
                    "text": text,
                }
            },
        )

    def find_references(self, uri: str, line: int, character: int, include_declaration: bool = False):
        """Request references for a position."""
        return self.request(
            "textDocument/references",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
                "context": {"includeDeclaration": include_declaration},
            },
        )

    def close(self):
        """Shutdown and exit the LSP server."""
        if not self.proc:
            return
        try:
            self.request("shutdown", {})
        finally:
            try:
                self.notify("exit", {})
            finally:
                self.proc.terminate()
                self.proc = None
                self._started = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
