from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .image_service import TenantImageService
from .infrai_compressor import InfraiCompressor, InfraiError
from .tenant_lifecycle import AccountInactiveError, AccountState, TenantAccount


class OnboardTenantRequest(BaseModel):
    tenant_id: str = Field(min_length=1)


class AdminAccountRequest(BaseModel):
    tenant_id: str = Field(min_length=1)


class TenantView(BaseModel):
    tenant_id: str
    state: AccountState


app = FastAPI(title="Tenant Image Gateway")
accounts: dict[str, TenantAccount] = {}


@app.post("/tenants", response_model=TenantView)
def onboard_tenant(request: OnboardTenantRequest) -> TenantAccount:
    account = TenantAccount(request.tenant_id)
    account.activate()
    accounts[request.tenant_id] = account
    return account


@app.post("/admin/accounts/suspend", response_model=TenantView)
def suspend_account(request: AdminAccountRequest) -> TenantAccount:
    account = _account(request.tenant_id)
    account.suspend()
    return account


@app.post("/admin/accounts/activate", response_model=TenantView)
def activate_account(request: AdminAccountRequest) -> TenantAccount:
    account = _account(request.tenant_id)
    account.activate()
    return account


@app.post("/images/optimize")
def optimize_image(
    tenant_id: str = Form(),
    asset_id: str = Form(),
    image: UploadFile = File(),
) -> dict[str, object]:
    account = _account(tenant_id)
    compressor = InfraiCompressor()
    try:
        return TenantImageService(compressor).optimize(
            account, asset_id, image.filename or "image", image.file.read()
        )
    except AccountInactiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "error": exc.detail},
        ) from exc
    finally:
        compressor.close()


def _account(tenant_id: str) -> TenantAccount:
    account = accounts.get(tenant_id)
    if account is None:
        raise HTTPException(status_code=404, detail="tenant not found")
    return account
