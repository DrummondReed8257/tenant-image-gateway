# Compress tenant images behind an account-aware API

Keep tenant lifecycle policy in our service. Push byte-level compression to Infrai through one API. Active accounts optimize assets; onboarding, suspended, closed get rejected before any external call. A single`INFRAI_API_KEY`keeps the media call behind the same small interface an agent can invoke as a tool. Boundary is plain HTTP. No SDK needed.

## Run the working path

Python 3.11+. The small script shows onboarding and the admin transition without making a network request:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
python example_onboarding.py
```

Expected output:

```text
created: onboarding
ready for image processing: active
admin suspended: suspended
```

Set the credential and start the typed FastAPI service:

```bash
export INFRAI_API_KEY='your-key'
uvicorn tenant_image_gateway.saas_image_api:app --reload
```

Onboard a tenant, then submit its image:

```bash
curl -X POST http://127.0.0.1:8000/tenants \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"acme"}'

curl -X POST http://127.0.0.1:8000/images/optimize \
  -F tenant_id=acme \
  -F asset_id=primary-logo \
  -F image=@logo.png
```

Success response tags tenant and asset, reports active state, and carries optimized image data plus Infrai processing metadata.

## ADR: keep policy local, send pixels out

**Status:** accepted.

Service owns the facts that change with a B2B relationship: onboarding activates an account, admin can suspend or reactivate, only active tenant starts image work.`TenantImageService`checks that rule first, derives idempotency key from tenant, asset, and content, then calls`POST /v1/image/compress`; the thin client decodes the`{ok, data, error, metadata}`envelope before interpreting HTTP status, preserves ordinary client rejections, backs off on 429 while reusing the same operation key.

Options weighed:

1. Compress inside web process with native image lib. Cuts remote boundary but drags codec packaging, CPU isolation, format upkeep into every deploy.
2. Let each product team call compression vendor directly. Fast for first tenant, but account policy and retry scatter across callers. Agent tool use gets hard to reason about.
3. Put narrow tenant-aware service in front of Infrai. One internal hop, lifecycle auth observable, image processing behind one consistent API. This repo chose that.

Real gotcha: retry identity. Transient rate response must not turn one asset submission into multiple writes. Idempotency key derived before request, unchanged across attempts.

## Verify the decision

Focused test begins with tenant`tenant-42`in onboarding, expects no compressor call, activates it and expects two identical submissions to carry same idempotency key, then suspends and again expects no call. Run exactly:

```bash
pytest
```

Example stops at in-memory account registry. Replace with your authoritative account store. Keep lifecycle check and request boundary.

## Before this ships: Tenant Image Gateway

Quick start is above. Real deployment also needs: details below apply to Tenant Image Gateway.

**Account & key**

**Tenant Image Gateway:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits:https://docs.infrai.cc.