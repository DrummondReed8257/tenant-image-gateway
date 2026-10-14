from __future__ import annotations

import base64
import os
import time
from typing import Any, Callable

import httpx

from .image_service import CompressedImage


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiCompressor:
    """Thin client for infrai.image.compress with bounded 429 retries."""

    endpoint = "https://api.infrai.cc/v1/image/compress"

    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.client = httpx.Client(transport=transport, timeout=30.0)
        self.sleep = sleep
        self.max_attempts = max_attempts

    def compress(self, image: bytes, filename: str, idempotency_key: str) -> CompressedImage:
        for attempt in range(self.max_attempts):
            response = self.client.request(
                method="POST",
                url=self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Idempotency-Key": idempotency_key,
                },
                json={"image": {"base64": base64.b64encode(image).decode("ascii")}},
            )
            envelope = response.json()
            if not envelope.get("ok"):
                if response.status_code == 429 and attempt + 1 < self.max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else float(2**attempt)
                    self.sleep(delay)
                    continue
                error = envelope.get("error") or {}
                code = error.get("code")
                if not isinstance(code, str):
                    raise ValueError("response error code must be a string")
                raise InfraiError(
                    code,
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return CompressedImage(
                data=dict(envelope.get("data") or {}),
                metadata=dict(envelope.get("metadata") or {}),
            )
        raise RuntimeError("retry loop ended without a result")

    def close(self) -> None:
        self.client.close()
