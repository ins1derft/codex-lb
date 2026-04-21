from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from typing import cast

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import HTTPConnection

from app.core.auth.api_key_cache import get_api_key_cache
from app.core.auth.dashboard_mode import DashboardAuthMode, get_dashboard_request_auth
from app.core.clients.usage import UsageFetchError, fetch_usage
from app.core.config.settings import get_settings
from app.core.config.settings_cache import get_settings_cache
from app.core.exceptions import DashboardAuthError, DashboardForbiddenError, ProxyAuthError, ProxyUpstreamError
from app.core.request_locality import is_local_request
from app.core.utils.time import utcnow
from app.db.session import get_background_session
from app.modules.accounts.repository import AccountsRepository
from app.modules.api_keys.repository import ApiKeysRepository
from app.modules.api_keys.service import ApiKeyData, ApiKeyInvalidError, ApiKeysService
from app.modules.dashboard_auth.service import DASHBOARD_SESSION_COOKIE, get_dashboard_session_store
from app.modules.users.repository import UsersRepository

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(description="API key (e.g. sk-clb-…)", auto_error=False)


@dataclass(frozen=True, slots=True)
class DashboardPrincipal:
    user_id: str
    username: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def set_openai_error_format(request: Request) -> None:
    request.state.error_format = "openai"


def set_dashboard_error_format(request: Request) -> None:
    request.state.error_format = "dashboard"


async def validate_proxy_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> ApiKeyData | None:
    authorization = None if credentials is None else f"Bearer {credentials.credentials}"
    return await validate_proxy_api_key_authorization(authorization, request=request)


async def validate_proxy_api_key_authorization(
    authorization: str | None,
    *,
    request: HTTPConnection | None = None,
) -> ApiKeyData | None:
    settings = await get_settings_cache().get()
    if not settings.api_key_auth_enabled:
        if request is not None and not is_local_request(request):
            if not _is_proxy_unauthenticated_socket_peer_allowed(request):
                raise ProxyAuthError("Proxy authentication must be configured before remote access is allowed")
        return None

    token = _extract_bearer_token(authorization)
    if not token:
        raise ProxyAuthError("Missing API key in Authorization header")

    return await _validate_api_key_token(token)


async def require_codex_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> ApiKeyData:
    token = _extract_bearer_token(None if credentials is None else f"Bearer {credentials.credentials}")
    if not token:
        raise ProxyAuthError("Missing API key in Authorization header")
    return await _validate_api_key_token(token)


async def _validate_api_key_token(token: str) -> ApiKeyData:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    cache = get_api_key_cache()
    cached = cast(ApiKeyData | None, await cache.get(token_hash))
    if cached is not None:
        if cached.expires_at is not None and cached.expires_at <= utcnow():
            await cache.invalidate(token_hash)
        else:
            return cached

    version_before_read = cache.version
    async with get_background_session() as session:
        service = ApiKeysService(ApiKeysRepository(session))
        try:
            validated = await service.validate_key(token)
        except ApiKeyInvalidError as exc:
            raise ProxyAuthError(str(exc)) from exc

        if validated.owner_user_id:
            users_repository = UsersRepository(session)
            owner = await users_repository.get_by_id(validated.owner_user_id)
            if owner is None or not owner.is_active:
                raise ProxyAuthError("Invalid API key")

        await cache.set(token_hash, validated, if_version=version_before_read)
        return validated


async def validate_usage_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> ApiKeyData:
    del request
    token = _extract_bearer_token(None if credentials is None else f"Bearer {credentials.credentials}")
    if not token:
        raise ProxyAuthError("Missing API key in Authorization header")
    return await _validate_api_key_token(token)


async def validate_dashboard_session(request: Request) -> None:
    request_auth = get_dashboard_request_auth(request)
    if request_auth is not None:
        actor = request_auth.actor or request_auth.mode.value
        request.state.dashboard_principal = DashboardPrincipal(
            user_id=actor,
            username=actor,
            role="admin",
        )
        return

    settings = await get_settings_cache().get()
    password_required = bool(settings.password_hash)
    requires_auth = password_required or settings.totp_required_on_login
    if get_dashboard_request_auth_mode() == DashboardAuthMode.TRUSTED_HEADER and not requires_auth:
        raise DashboardAuthError("Reverse proxy authentication is required", code="proxy_auth_required")
    if not requires_auth:
        if not is_local_request(request):
            raise DashboardAuthError(
                "Remote bootstrap is required before dashboard access is allowed",
                code="bootstrap_required",
            )
        return

    if not password_required and settings.totp_required_on_login:
        logger.warning(
            "dashboard_auth_migration_inconsistency password_hash is NULL"
            " while totp_required_on_login=true metric=dashboard_auth_migration_inconsistency"
        )

    session_id = request.cookies.get(DASHBOARD_SESSION_COOKIE)
    state = get_dashboard_session_store().get(session_id)
    if state is None:
        raise DashboardAuthError("Authentication is required")
    if password_required and not state.password_verified:
        raise DashboardAuthError("Authentication is required")
    if settings.totp_required_on_login and not state.totp_verified:
        raise DashboardAuthError("TOTP verification is required for dashboard access", code="totp_required")

    async with get_background_session() as session:
        users_repository = UsersRepository(session)
        user = await users_repository.get_by_id(state.user_id)
        if user is None or not user.is_active:
            raise DashboardAuthError("Authentication is required")
        request.state.dashboard_principal = DashboardPrincipal(
            user_id=user.id,
            username=user.username,
            role=user.role.value,
        )


async def get_dashboard_principal(request: Request) -> DashboardPrincipal:
    principal = getattr(request.state, "dashboard_principal", None)
    if not isinstance(principal, DashboardPrincipal):
        await validate_dashboard_session(request)
        principal = getattr(request.state, "dashboard_principal", None)
    if not isinstance(principal, DashboardPrincipal):
        raise DashboardAuthError("Authentication is required")
    return principal


async def require_admin_principal(
    principal: DashboardPrincipal = Depends(get_dashboard_principal),
) -> DashboardPrincipal:
    if not principal.is_admin:
        raise DashboardForbiddenError("Admin role is required")
    return principal


def get_dashboard_request_auth_mode() -> DashboardAuthMode:
    return get_settings().dashboard_auth_mode


def _is_proxy_unauthenticated_socket_peer_allowed(request: HTTPConnection) -> bool:
    socket_host = request.client.host if request.client else None
    if socket_host is None:
        return False

    try:
        socket_ip = ip_address(socket_host)
    except ValueError:
        return False

    configured_cidrs = get_settings().proxy_unauthenticated_client_cidrs
    return any(socket_ip in ip_network(cidr, strict=False) for cidr in configured_cidrs)


async def validate_codex_usage_identity(request: Request) -> ApiKeyData | None:
    token = _extract_bearer_token(request.headers.get("Authorization"))
    if not token:
        raise ProxyAuthError("Missing ChatGPT token in Authorization header")

    raw_account_id = request.headers.get("chatgpt-account-id")
    account_id = raw_account_id.strip() if raw_account_id else ""
    if not account_id:
        if token.startswith("sk-clb-"):
            return await _validate_api_key_token(token)
        raise ProxyAuthError("Missing chatgpt-account-id header")

    async with get_background_session() as session:
        accounts_repo = AccountsRepository(session)
        is_authorized = await accounts_repo.exists_active_chatgpt_account_id(account_id)
    if not is_authorized:
        raise ProxyAuthError("Unknown or inactive chatgpt-account-id")

    try:
        await fetch_usage(access_token=token, account_id=account_id)
    except UsageFetchError as exc:
        if exc.status_code == 429:
            from app.core.exceptions import ProxyRateLimitError

            raise ProxyRateLimitError(exc.message) from exc
        if exc.status_code in (401, 403):
            raise ProxyAuthError("Invalid ChatGPT token or chatgpt-account-id") from exc
        raise ProxyUpstreamError("Unable to validate ChatGPT credentials at this time") from exc
    return None


def _extract_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    prefix = "bearer "
    value = authorization.strip()
    if not value.lower().startswith(prefix):
        return None
    token = value[len(prefix) :].strip()
    if not token:
        return None
    return token
