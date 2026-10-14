from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol

from .tenant_lifecycle import TenantAccount


@dataclass(frozen=True)
class CompressedImage:
    data: dict[str, Any]
    metadata: dict[str, Any]


class Compressor(Protocol):
    def compress(self, image: bytes, filename: str, idempotency_key: str) -> CompressedImage:
        """Return the compressed image envelope payload."""


class TenantImageService:
    def __init__(self, compressor: Compressor) -> None:
        self.compressor = compressor

    def optimize(
        self,
        account: TenantAccount,
        asset_id: str,
        filename: str,
        image: bytes,
    ) -> dict[str, Any]:
        account.require_image_processing()
        digest = hashlib.sha256(image).hexdigest()[:16]
        operation_key = f"tenant-image:{account.tenant_id}:{asset_id}:{digest}"
        result = self.compressor.compress(image, filename, operation_key)
        return {
            "tenant_id": account.tenant_id,
            "asset_id": asset_id,
            "account_state": account.state,
            "image": result.data,
            "processing": result.metadata,
        }
