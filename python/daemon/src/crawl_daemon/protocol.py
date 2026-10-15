"""The wire format: one JSON object per line, each way.

A request is ``{"op": "...", "token": "...", "args": {...}}``. The response is
``{"ok": true, "result": ...}`` or ``{"ok": false, "error": {"code": "...",
"message": "..."}}``, where ``code`` is one of the :class:`DaemonError` codes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from crawl_daemon.models import ERRORS_BY_CODE, DaemonError, InternalError, InvalidRequestError

MAX_LINE_BYTES = 1024 * 1024
"""Longest request or response line accepted, newline included."""

OPERATIONS = frozenset({"ping", "submit", "get", "list", "pages", "links", "cancel", "shutdown"})


@dataclass(frozen=True, slots=True)
class Request:
    op: str
    token: str | None = None
    args: dict[str, Any] = field(default_factory=dict)


def _line(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"


def encode_request(request: Request) -> bytes:
    return _line({"op": request.op, "token": request.token, "args": request.args})


def decode_request(line: bytes) -> Request:
    """Parse a request line. The operation name is checked later, after the token."""
    try:
        data = json.loads(line)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidRequestError(f"request is not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise InvalidRequestError("request must be a JSON object")
    op, token, args = data.get("op"), data.get("token"), data.get("args", {})
    if not isinstance(op, str):
        raise InvalidRequestError("request needs an 'op' string")
    if token is not None and not isinstance(token, str):
        raise InvalidRequestError("'token' must be a string")
    if not isinstance(args, dict):
        raise InvalidRequestError("'args' must be an object")
    return Request(op, token, args)


def encode_ok(result: Any) -> bytes:
    return _line({"ok": True, "result": result})


def encode_error(error: DaemonError) -> bytes:
    return _line({"ok": False, "error": {"code": error.code, "message": str(error)}})


def decode_response(line: bytes) -> Any:
    """Return a response's result, or raise the :class:`DaemonError` it reports."""
    try:
        data = json.loads(line)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InternalError(f"the daemon sent an unreadable response: {exc}") from None
    if not isinstance(data, dict) or not isinstance(data.get("ok"), bool):
        raise InternalError("the daemon sent an unexpected response")
    if data["ok"]:
        return data.get("result")
    error = data.get("error")
    if not isinstance(error, dict):
        raise InternalError("the daemon sent an error without details")
    cls = ERRORS_BY_CODE.get(str(error.get("code")), InternalError)
    raise cls(str(error.get("message", "unknown error")))
