import time
import uuid
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from jobhunt_api.redact import redact
from jobhunt_api.routers import (
    agents,
    applications,
    approvals,
    dashboard,
    deploy,
    dev,
    discovery,
    documents,
    health,
    identity,
    inbox,
    matching,
    notifications,
    outreach,
    profile,
    sources,
    stubs,
    uat,
)
from jobhunt_api.settings import settings

app = FastAPI(title="Job-hunt API", version="0.1.0", openapi_url="/openapi.json", docs_url="/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_hits: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def observability(request: Request, call_next):
    cid = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    request.state.correlation_id = cid
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _hits[ip]
    _hits[ip] = [t for t in bucket if now - t < 60]
    if len(_hits[ip]) >= settings.rate_limit_per_minute:
        return JSONResponse({"detail": "rate limited"}, status_code=429, headers={"x-correlation-id": cid})
    _hits[ip].append(now)
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        print(redact(f"error cid={cid} {exc}"))
        return JSONResponse({"detail": "internal error"}, status_code=500, headers={"x-correlation-id": cid})
    response.headers["x-correlation-id"] = cid
    print(redact(f"cid={cid} {request.method} {request.url.path} {response.status_code}"))
    return response


prefix = "/api/v1"
app.include_router(health.router, prefix=prefix)
app.include_router(dev.router, prefix=prefix)
app.include_router(identity.router, prefix=prefix)
app.include_router(profile.router, prefix=prefix)
app.include_router(sources.router, prefix=prefix)
app.include_router(discovery.router, prefix=prefix)
app.include_router(inbox.router, prefix=prefix)
app.include_router(matching.router, prefix=prefix)
app.include_router(approvals.router, prefix=prefix)
app.include_router(documents.router, prefix=prefix)
app.include_router(agents.router, prefix=prefix)
app.include_router(notifications.router, prefix=prefix)
app.include_router(outreach.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)
app.include_router(applications.router, prefix=prefix)
app.include_router(deploy.router, prefix=prefix)
app.include_router(stubs.router, prefix=prefix)
app.include_router(uat.router, prefix=prefix)
