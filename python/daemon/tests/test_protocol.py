import json

import pytest

from crawl_daemon.models import (
    ConflictError,
    InternalError,
    InvalidRequestError,
    NotFoundError,
    UnauthorizedError,
)
from crawl_daemon.protocol import (
    Request,
    decode_request,
    decode_response,
    encode_error,
    encode_ok,
    encode_request,
)


def test_request_round_trip() -> None:
    request = Request("submit", "secret", {"url": "https://example.com/", "max_pages": 5})
    line = encode_request(request)
    assert line.endswith(b"\n")
    assert line.count(b"\n") == 1
    assert decode_request(line) == request


def test_request_defaults() -> None:
    assert decode_request(b'{"op": "ping"}') == Request("ping", None, {})


@pytest.mark.parametrize(
    ("line", "message"),
    [
        (b"not json", "not valid JSON"),
        (b"\xff\xfe", "not valid JSON"),
        (b"[1, 2]", "JSON object"),
        (b'{"token": "x"}', "'op'"),
        (b'{"op": 3}', "'op'"),
        (b'{"op": "ping", "token": 5}', "'token'"),
        (b'{"op": "ping", "args": []}', "'args'"),
    ],
)
def test_malformed_requests(line: bytes, message: str) -> None:
    with pytest.raises(InvalidRequestError, match=message):
        decode_request(line)


def test_unknown_op_is_left_to_the_server() -> None:
    assert decode_request(b'{"op": "explode", "token": "t"}').op == "explode"


def test_ok_response() -> None:
    assert decode_response(encode_ok({"id": "abc"})) == {"id": "abc"}
    assert decode_response(encode_ok(None)) is None


@pytest.mark.parametrize(
    "error",
    [
        InvalidRequestError("bad"),
        UnauthorizedError("who?"),
        NotFoundError("gone"),
        ConflictError("already completed"),
        InternalError("oops"),
    ],
)
def test_error_responses_raise_their_type(error: Exception) -> None:
    line = encode_error(error)  # type: ignore[arg-type]
    assert json.loads(line)["error"]["code"] == error.code  # type: ignore[attr-defined]
    with pytest.raises(type(error), match=str(error)):
        decode_response(line)


@pytest.mark.parametrize(
    "line",
    [b"garbage", b"[]", b'{"ok": "yes"}', b'{"ok": false}', b'{"ok": false, "error": "x"}'],
)
def test_unexpected_responses(line: bytes) -> None:
    with pytest.raises(InternalError):
        decode_response(line)


def test_unknown_error_code_is_internal() -> None:
    with pytest.raises(InternalError, match="strange"):
        decode_response(b'{"ok": false, "error": {"code": "weird", "message": "strange"}}')
