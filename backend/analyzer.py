"""Analyzes captured HTTP responses and produces a plain-language diagnosis."""

KNOWN_API_PROVIDERS = ["stripe.com", "twilio.com", "sendgrid.com"]

STATUS_TEXT = {
    200: "OK", 201: "Created", 202: "Accepted", 204: "No Content",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
    422: "Unprocessable Entity", 429: "Too Many Requests",
    500: "Internal Server Error", 502: "Bad Gateway", 503: "Service Unavailable",
    504: "Gateway Timeout",
}


def _get_header(headers, name):
    if not headers:
        return None
    lname = name.lower()
    for k, v in headers.items():
        if k.lower() == lname:
            return v
    return None


def _check_header_issues(headers, body, target_url):
    """Header-level checks that apply regardless of status code."""
    issues = []
    auth = _get_header(headers, "Authorization")
    content_type = _get_header(headers, "Content-Type")

    if body is not None and not content_type:
        issues.append({"field": "Content-Type", "issue": "Missing Content-Type header despite a request body being present"})

    if auth is not None and auth.strip() == "":
        issues.append({"field": "Authorization", "issue": "Authorization header is present but empty"})
    elif auth is not None and not (auth.startswith("Bearer") or auth.startswith("Basic")):
        issues.append({"field": "Authorization", "issue": "Authorization value doesn't start with 'Bearer' or 'Basic'"})

    if target_url and any(p in target_url for p in KNOWN_API_PROVIDERS):
        has_api_key = _get_header(headers, "X-API-Key") is not None
        if not has_api_key and not auth:
            issues.append({"field": "X-API-Key", "issue": "No API key header found for a known provider endpoint"})

    return issues


def _extract_validation_errors(body):
    """Best-effort extraction of field-level validation errors from a JSON body."""
    errors = []
    if not isinstance(body, dict):
        return errors

    # Common shapes: {"errors": [...]}, {"detail": [...]}, {"error": {"message": ...}}
    for key in ("errors", "detail", "error_details"):
        val = body.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    field = item.get("field") or item.get("param") or item.get("loc") or "unknown"
                    if isinstance(field, list):
                        field = ".".join(str(f) for f in field)
                    msg = item.get("message") or item.get("msg") or str(item)
                    errors.append({"field": str(field), "issue": msg})
                else:
                    errors.append({"field": "unknown", "issue": str(item)})

    error_obj = body.get("error")
    if isinstance(error_obj, dict):
        field = error_obj.get("param") or error_obj.get("field") or "unknown"
        msg = error_obj.get("message")
        if msg:
            errors.append({"field": str(field), "issue": msg})

    return errors


def analyze(status, headers, body, target_url, req_headers, req_body, timed_out=False):
    headers = headers or {}
    req_headers = req_headers or {}
    detected_issues = _check_header_issues(req_headers, req_body, target_url)

    if timed_out:
        return {
            "severity": "error",
            "summary": "Request timed out",
            "error_code": "TIMEOUT",
            "explanation": "The request timed out after 10 seconds. The server may be overloaded or the endpoint may be slow under load.",
            "suggestion": "Retry the request, check the API provider's status page, or increase the timeout if this endpoint is known to be slow.",
            "detected_issues": detected_issues,
        }

    if status is None:
        return {
            "severity": "error",
            "summary": "Request failed",
            "error_code": "CONNECTION_ERROR",
            "explanation": "The request could not be completed. This usually means a DNS failure, a refused connection, or an invalid URL.",
            "suggestion": "Check that the target URL is correct and reachable, and that there is network connectivity to the host.",
            "detected_issues": detected_issues,
        }

    status_text = STATUS_TEXT.get(status, "")

    if 200 <= status < 300:
        return {
            "severity": "success",
            "summary": f"{status} {status_text}".strip(),
            "error_code": "OK",
            "explanation": "The request completed successfully.",
            "suggestion": "No action needed.",
            "detected_issues": detected_issues,
        }

    if status == 400:
        validation_errors = _extract_validation_errors(body)
        detected_issues.extend(validation_errors)
        return {
            "severity": "error",
            "summary": "400 Bad Request",
            "error_code": "VALIDATION_ERROR",
            "explanation": "The API rejected the request body or parameters as malformed.",
            "suggestion": "Check the fields listed below against the API's documented schema.",
            "detected_issues": detected_issues,
        }

    if status == 401:
        auth = _get_header(req_headers, "Authorization")
        if not auth:
            detected_issues.append({"field": "Authorization", "issue": "Authorization header missing"})
        elif not auth.startswith("Bearer ") and not auth.startswith("Basic "):
            detected_issues.append({"field": "Authorization", "issue": "Bearer token missing or malformed"})
        elif auth.startswith("Bearer ") and len(auth.split(" ", 1)[1].strip()) == 0:
            detected_issues.append({"field": "Authorization", "issue": "Bearer token is empty"})
        return {
            "severity": "error",
            "summary": "401 Unauthorized",
            "error_code": "AUTH_FAILED",
            "explanation": "The API rejected the request due to missing or invalid credentials.",
            "suggestion": "Verify the API key is active and not expired. Check that the Authorization header format matches what the API expects (e.g. 'Bearer <token>' vs 'Token <token>').",
            "detected_issues": detected_issues,
        }

    if status == 403:
        return {
            "severity": "error",
            "summary": "403 Forbidden",
            "error_code": "FORBIDDEN",
            "explanation": "Authenticated but not authorized. The API key may lack the required scope or permission for this endpoint.",
            "suggestion": "Check the API key's permissions/scopes and confirm it is allowed to access this resource.",
            "detected_issues": detected_issues,
        }

    if status == 404:
        detected_issues.append({"field": "URL", "issue": "Path may be misspelled, use the wrong API version, or reference a resource ID that doesn't exist"})
        return {
            "severity": "error",
            "summary": "404 Not Found",
            "error_code": "NOT_FOUND",
            "explanation": "The endpoint does not exist. This usually means a typo in the path, a wrong API version, or the resource ID doesn't exist.",
            "suggestion": "Double check the URL path against the API's documentation, including the version prefix.",
            "detected_issues": detected_issues,
        }

    if status == 422:
        validation_errors = _extract_validation_errors(body)
        detected_issues.extend(validation_errors)
        return {
            "severity": "error",
            "summary": "422 Unprocessable Entity",
            "error_code": "VALIDATION_ERROR",
            "explanation": "The request was well-formed but failed validation on one or more fields.",
            "suggestion": "Review each validation error below and correct the corresponding field.",
            "detected_issues": detected_issues,
        }

    if status == 429:
        retry_after = _get_header(headers, "Retry-After")
        suggestion = "Slow down your request rate and implement backoff."
        if retry_after:
            suggestion += f" The API says to retry after {retry_after} seconds."
            detected_issues.append({"field": "Retry-After", "issue": f"Server requests waiting {retry_after}s before retrying"})
        return {
            "severity": "warning",
            "summary": "429 Too Many Requests",
            "error_code": "RATE_LIMITED",
            "explanation": "Rate limit hit. Too many requests sent in a short window.",
            "suggestion": suggestion,
            "detected_issues": detected_issues,
        }

    if 500 <= status < 600:
        return {
            "severity": "error",
            "summary": f"{status} {status_text}".strip(),
            "error_code": "SERVER_ERROR",
            "explanation": "Server-side error, not caused by your request. Check the API provider's status page.",
            "suggestion": "Retry with exponential backoff. If the issue persists, check the provider's status page or contact their support.",
            "detected_issues": detected_issues,
        }

    if 300 <= status < 400:
        return {
            "severity": "warning",
            "summary": f"{status} {status_text}".strip(),
            "error_code": "REDIRECT",
            "explanation": "The API responded with a redirect rather than the expected resource.",
            "suggestion": "Confirm the request URL and whether the client should follow the redirect automatically.",
            "detected_issues": detected_issues,
        }

    return {
        "severity": "warning",
        "summary": f"{status} {status_text}".strip() if status else "Unknown response",
        "error_code": "UNKNOWN",
        "explanation": "The response did not match a recognized pattern.",
        "suggestion": "Inspect the raw response body and headers for details.",
        "detected_issues": detected_issues,
    }
