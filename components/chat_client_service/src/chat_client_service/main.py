"""FastAPI service for chat client."""
import os
import secrets
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from slack_client_impl.client import SlackClient
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(
    title="Chat Client Service",
    description="Slack chat client service API",
    version="0.1.0",
)

_session_secret = os.getenv("SESSION_SECRET_KEY")
if not _session_secret:
    msg = (
        "SESSION_SECRET_KEY environment variable must be set "
        "to enable OAuth session storage."
    )
    raise RuntimeError(msg)

app.add_middleware(
    SessionMiddleware,
    secret_key=_session_secret,
    same_site="lax",
    https_only=os.getenv("ENV", "local").lower() in {"prod", "production"},
)


def _slack_oauth_scopes() -> str:
    return os.getenv(
        "SLACK_SCOPES",
        "chat:write,channels:read,channels:history",
    )


def _slack_redirect_uri() -> str:
    return os.getenv(
        "SLACK_REDIRECT_URI",
        "http://localhost:8000/auth/callback",
    )


def _require_slack_token(request: Request) -> str:
    token = request.session.get("slack_bot_token")
    if not isinstance(token, str) or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Visit /auth/login first.",
        )
    return token


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Status ok

    """
    return {"status": "ok"}


@app.get("/auth/login")
def auth_login(request: Request) -> RedirectResponse:
    """Redirect to Slack OAuth login.

    Returns:
        Redirect to Slack auth URL

    """
    client_id = os.getenv("SLACK_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SLACK_CLIENT_ID environment variable must be set.",
        )

    state = secrets.token_urlsafe(32)
    request.session["slack_oauth_state"] = state

    params = {
        "client_id": client_id,
        "scope": _slack_oauth_scopes(),
        "redirect_uri": _slack_redirect_uri(),
        "state": state,
    }
    slack_auth_url = f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"
    return RedirectResponse(url=slack_auth_url, status_code=status.HTTP_302_FOUND)


@app.get("/auth/callback")
async def auth_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
) -> dict[str, str]:
    """Handle OAuth callback from Slack.

    Args:
        request: Incoming HTTP request (used for cookie session)
        code: Authorization code from Slack
        state: CSRF protection state returned by Slack
        error: Error string returned by Slack, if any

    Returns:
        Success message

    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Slack OAuth error: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No code provided.",
        )

    expected_state = request.session.get("slack_oauth_state")
    if not isinstance(expected_state, str) or not expected_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth state in session. Start at /auth/login.",
        )
    if not state or state != expected_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state.",
        )

    client_id = os.getenv("SLACK_CLIENT_ID")
    client_secret = os.getenv("SLACK_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SLACK_CLIENT_ID and SLACK_CLIENT_SECRET must be set.",
        )

    import httpx

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": _slack_redirect_uri(),
            },
        )
        data = resp.json()

    if data.get("ok") is not True:
        err = data.get("error", "unknown_error")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Slack token exchange failed: {err}",
        )

    bot_token = data.get("access_token")
    if not isinstance(bot_token, str) or not bot_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Slack response missing access_token.",
        )

    request.session.pop("slack_oauth_state", None)
    request.session["slack_bot_token"] = bot_token

    team = data.get("team")
    if isinstance(team, dict):
        name = team.get("name")
        if isinstance(name, str) and name:
            request.session["slack_team_name"] = name

    return {"status": "ok", "message": "Authentication successful"}


@app.post("/auth/logout")
def auth_logout(request: Request) -> dict[str, str]:
    """Clear the current user's session."""
    request.session.clear()
    return {"status": "ok"}


@app.get("/channels")
def list_channels(request: Request) -> dict[str, list[dict[str, str | bool]]]:
    """List all Slack channels.

    Args:
        request: Incoming HTTP request (used for cookie session)

    Returns:
        List of channels

    """
    token = _require_slack_token(request)
    client = SlackClient(token)
    channels = client.list_channels()
    return {
        "channels": [
            {
                "channel_id": ch.channel_id,
                "name": ch.name,
                "is_private": ch.is_private,
            }
            for ch in channels
        ],
    }


@app.post("/messages")
def send_message(
    request: Request,
    channel: str,
    text: str,
) -> dict[str, str | bool]:
    """Send a message to a Slack channel.

    Args:
        request: Incoming HTTP request (used for cookie session)
        channel: Channel ID or name
        text: Message text

    Returns:
        SendMessageResponse details

    """
    token = _require_slack_token(request)
    client = SlackClient(token)
    response = client.send_message(channel=channel, text=text)
    return {
        "message_id": response.message_id,
        "channel": response.channel,
        "timestamp": response.timestamp,
        "ok": response.ok,
    }


@app.get("/messages")
def get_messages(
    request: Request,
    channel: str,
    limit: int = 10,
    cursor: str = "",
) -> dict[str, list[dict[str, str]]]:
    """Get messages from a Slack channel.

    Args:
        request: Incoming HTTP request (used for cookie session)
        channel: Channel ID or name
        limit: Max messages to return
        cursor: Pagination cursor

    Returns:
        List of messages

    """
    token = _require_slack_token(request)
    client = SlackClient(token)
    messages = client.get_messages(
        channel=channel,
        limit=limit,
        cursor=cursor or None,
    )
    return {
        "messages": [
            {
                "message_id": msg.message_id,
                "channel": msg.channel,
                "text": msg.text,
                "sender": msg.sender,
                "timestamp": msg.timestamp,
            }
            for msg in messages
        ],
    }
