from fastapi import APIRouter

from jobhunt_api.services import deploy_checks

router = APIRouter(tags=["deploy"])


@router.get("/deploy/external-gmail-readiness")
def external_gmail_readiness() -> dict:
    report = deploy_checks.external_gmail_deployment_ready()
    report["browser_env_leak_detected"] = not deploy_checks.assert_no_browser_feature_leak()
    return report
