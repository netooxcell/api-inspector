"""Forwards a captured request descriptor to the real API using httpx."""
import os
import time

import httpx

DEFAULT_TIMEOUT = float(os.environ.get("DEFAULT_TIMEOUT", "10"))


class ForwardResult:
    def __init__(self, status=None, headers=None, body=None, duration_ms=0, timed_out=False):
        self.status = status
        self.headers = headers or {}
        self.body = body
        self.duration_ms = duration_ms
        self.timed_out = timed_out


async def forward_request(method, target_url, headers=None, body=None, query_params=None):
    headers = headers or {}
    query_params = query_params or {}
    start = time.perf_counter()

    kwargs = {"headers": headers, "params": query_params}
    if body is not None:
        if isinstance(body, (dict, list)):
            kwargs["json"] = body
        else:
            kwargs["content"] = str(body)

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
            response = await client.request(method.upper(), target_url, **kwargs)
        duration_ms = int((time.perf_counter() - start) * 1000)

        try:
            response_body = response.json()
        except ValueError:
            response_body = response.text

        return ForwardResult(
            status=response.status_code,
            headers=dict(response.headers),
            body=response_body,
            duration_ms=duration_ms,
        )
    except httpx.TimeoutException:
        duration_ms = int((time.perf_counter() - start) * 1000)
        return ForwardResult(duration_ms=duration_ms, timed_out=True)
    except httpx.RequestError as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        return ForwardResult(
            status=None,
            headers={},
            body={"error": str(exc)},
            duration_ms=duration_ms,
        )


HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}


class RawForwardResult(ForwardResult):
    def __init__(self, *args, raw_content=b"", content_type="", **kwargs):
        super().__init__(*args, **kwargs)
        self.raw_content = raw_content
        self.content_type = content_type


async def forward_raw(method, upstream_url, headers, raw_body, query_params=None):
    """Forwards an already-received client request verbatim to an upstream host,
    preserving raw bytes so binary responses (images, fonts) don't get corrupted."""
    query_params = query_params or {}
    forward_headers = {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}
    start = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
            response = await client.request(
                method.upper(), upstream_url,
                headers=forward_headers, params=query_params,
                content=raw_body if raw_body else None,
            )
        duration_ms = int((time.perf_counter() - start) * 1000)
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type or "text/" in content_type or "javascript" in content_type:
            try:
                body_for_storage = response.json()
            except ValueError:
                body_for_storage = response.text
        else:
            body_for_storage = f"<binary content, {len(response.content)} bytes, {content_type or 'unknown type'}>"

        return RawForwardResult(
            status=response.status_code,
            headers=dict(response.headers),
            body=body_for_storage,
            duration_ms=duration_ms,
            raw_content=response.content,
            content_type=content_type,
        )
    except httpx.TimeoutException:
        duration_ms = int((time.perf_counter() - start) * 1000)
        return RawForwardResult(duration_ms=duration_ms, timed_out=True)
    except httpx.RequestError as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        return RawForwardResult(
            status=None, headers={}, body={"error": str(exc)}, duration_ms=duration_ms,
        )
