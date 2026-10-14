import base64
import json

import httpx
import pytest

from tenant_image_gateway.image_service import CompressedImage, TenantImageService
from tenant_image_gateway.infrai_compressor import InfraiCompressor
from tenant_image_gateway.tenant_lifecycle import AccountInactiveError, TenantAccount


class RecordingCompressor:
    def __init__(self) -> None:
        self.keys: list[str] = []

    def compress(self, image: bytes, filename: str, idempotency_key: str) -> CompressedImage:
        self.keys.append(idempotency_key)
        return CompressedImage(
            data={"id": "optimized-logo"},
            metadata={"vendor": "selected"},
        )


def test_infrai_compressor_sends_json_image() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["content-type"] == "application/json"
        assert request.headers["Idempotency-Key"] == "operation-1"
        assert json.loads(request.content) == {
            "image": {"base64": base64.b64encode(b"image bytes").decode("ascii")}
        }
        return httpx.Response(200, json={"ok": True, "data": {}, "metadata": {}})

    compressor = InfraiCompressor(api_key="test", transport=httpx.MockTransport(respond))
    try:
        compressor.compress(b"image bytes", "image.png", "operation-1")
    finally:
        compressor.close()


def test_account_lifecycle_controls_processing_and_retries_are_stable() -> None:
    account = TenantAccount("tenant-42")
    compressor = RecordingCompressor()
    service = TenantImageService(compressor)

    with pytest.raises(AccountInactiveError):
        service.optimize(account, "logo", "logo.png", b"same pixels")
    assert compressor.keys == []

    account.activate()
    first = service.optimize(account, "logo", "logo.png", b"same pixels")
    second = service.optimize(account, "logo", "logo.png", b"same pixels")

    assert first["account_state"] == "active"
    assert first["image"] == {"id": "optimized-logo"}
    assert compressor.keys[0] == compressor.keys[1]

    account.suspend()
    with pytest.raises(AccountInactiveError):
        service.optimize(account, "logo", "logo.png", b"same pixels")
    assert len(compressor.keys) == 2
