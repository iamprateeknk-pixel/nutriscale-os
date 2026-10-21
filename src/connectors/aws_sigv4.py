"""AWS Signature V4 — Amazon SP-API har request par ye sign mangta hai.
Pure Python (hashlib/hmac) — koi bahari library nahi.
"""
import hashlib, hmac, datetime

def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

def sign_headers(host: str, path: str, query: str, region: str, service: str,
                 access_key: str, secret_key: str, extra_headers: dict = None,
                 method: str = "GET", payload: bytes = b"", now: datetime.datetime = None) -> dict:
    now = now or datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ"); date_stamp = now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(payload).hexdigest()
    headers = {"host": host, "x-amz-date": amz_date}
    if extra_headers: headers.update({k.lower(): v for k, v in extra_headers.items()})
    signed_keys = sorted(headers)
    canonical_headers = "".join(f"{k}:{headers[k].strip()}\n" for k in signed_keys)
    signed_headers = ";".join(signed_keys)
    canonical_request = "\n".join([method, path, query, canonical_headers, signed_headers, payload_hash])
    scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope,
                                hashlib.sha256(canonical_request.encode()).hexdigest()])
    k = _sign(("AWS4" + secret_key).encode(), date_stamp)
    k = _sign(k, region); k = _sign(k, service); k = _sign(k, "aws4_request")
    signature = hmac.new(k, string_to_sign.encode(), hashlib.sha256).hexdigest()
    out = dict(extra_headers or {}); out["x-amz-date"] = amz_date
    out["Authorization"] = (f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
                            f"SignedHeaders={signed_headers}, Signature={signature}")
    return out
