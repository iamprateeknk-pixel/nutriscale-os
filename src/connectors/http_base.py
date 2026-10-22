"""HTTP layer — saare connectors isi se baat karenge.
Retry: 429 (rate limit) aur 5xx par backoff ke saath dobara. 4xx par turant saaf error.
Transport injectable hai taaki tests me asal internet ke bina parakh ho sake.
"""
import json, time, urllib.request, urllib.error

class APIError(Exception):
    def __init__(self, status, body, url):
        super().__init__(f"API error {status} on {url}: {str(body)[:300]}")
        self.status, self.body = status, body

def _urllib_transport(req: dict):
    r = urllib.request.Request(req["url"], method=req["method"],
                               data=req.get("body_bytes"), headers=req.get("headers", {}))
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try: body = json.loads(raw)
        except Exception: body = {"raw": raw}
        return e.code, body

def _urllib_raw_transport(req: dict):
    r = urllib.request.Request(req["url"], method=req["method"],
                               data=req.get("body_bytes"), headers=req.get("headers", {}))
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

def request_raw(method: str, url: str, headers: dict = None, transport=None,
                retries: int = 3, sleep=time.sleep) -> bytes:
    """Bytes wala download (report ki gzip file ke liye). 429/5xx par backoff retry (INT-02)."""
    req = {"method": method, "url": url, "headers": dict(headers or {}), "body_bytes": None}
    transport = transport or _urllib_raw_transport
    for attempt in range(retries + 1):
        status, body = transport(req)
        if 200 <= status < 300: return body
        if status in (429, 500, 502, 503, 504) and attempt < retries:
            sleep(min(2 ** attempt, 8)); continue
        raise APIError(status, str(body)[:200], url)
    raise APIError(0, {}, url)

def request_json(method: str, url: str, headers: dict = None, json_body: dict = None,
                 form_body: dict = None, transport=None, retries: int = 3, sleep=time.sleep) -> dict:
    body_bytes, hdrs = None, dict(headers or {})
    if json_body is not None:
        body_bytes = json.dumps(json_body).encode(); hdrs["Content-Type"] = "application/json"
    elif form_body is not None:
        from urllib.parse import urlencode
        body_bytes = urlencode(form_body).encode(); hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    req = {"method": method, "url": url, "headers": hdrs, "body_bytes": body_bytes}
    transport = transport or _urllib_transport
    for attempt in range(retries + 1):
        status, body = transport(req)
        if 200 <= status < 300: return body
        if status in (429, 500, 502, 503, 504) and attempt < retries:
            sleep(min(2 ** attempt, 8)); continue
        raise APIError(status, body, url)
    raise APIError(0, {}, url)  # yahan pahuncha matlab retries khatm
