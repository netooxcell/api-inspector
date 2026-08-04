import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATABASE_PATH = os.environ.get("DATABASE_PATH", "./requests.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_id   INTEGER,
  method      TEXT,
  target_url  TEXT,
  req_headers TEXT,
  req_body    TEXT,
  req_params  TEXT,
  res_status  INTEGER,
  res_headers TEXT,
  res_body    TEXT,
  duration_ms INTEGER,
  severity    TEXT,
  summary     TEXT,
  error_code  TEXT,
  explanation TEXT,
  suggestion  TEXT,
  detected_issues TEXT,
  timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def _connect():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute(SCHEMA)


def _dump(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)


def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    for field in ("req_headers", "req_params", "res_headers", "detected_issues"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
        else:
            d[field] = {} if field != "detected_issues" else []
    for field in ("req_body", "res_body"):
        raw = d.get(field)
        if raw:
            try:
                d[field] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def create_pending(method, target_url, headers, body, params, parent_id=None):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO requests
               (parent_id, method, target_url, req_headers, req_body, req_params, severity)
               VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
            (parent_id, method, target_url, _dump(headers), _dump(body), _dump(params)),
        )
        return cur.lastrowid


def complete_request(record_id, res_status, res_headers, res_body, duration_ms, analysis):
    with get_conn() as conn:
        conn.execute(
            """UPDATE requests SET
                 res_status = ?, res_headers = ?, res_body = ?, duration_ms = ?,
                 severity = ?, summary = ?, error_code = ?, explanation = ?,
                 suggestion = ?, detected_issues = ?
               WHERE id = ?""",
            (
                res_status,
                _dump(res_headers),
                _dump(res_body),
                duration_ms,
                analysis["severity"],
                analysis["summary"],
                analysis["error_code"],
                analysis["explanation"],
                analysis["suggestion"],
                _dump(analysis["detected_issues"]),
                record_id,
            ),
        )


def get_request(record_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM requests WHERE id = ?", (record_id,)).fetchone()
        return row_to_dict(row)


def list_requests(limit=50, status="all"):
    query = "SELECT * FROM requests"
    args = []
    if status and status != "all":
        query += " WHERE severity = ?"
        args.append(status)
    query += " ORDER BY timestamp DESC LIMIT ?"
    args.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, args).fetchall()
        return [row_to_dict(r) for r in rows]


def clear_all():
    with get_conn() as conn:
        conn.execute("DELETE FROM requests")
