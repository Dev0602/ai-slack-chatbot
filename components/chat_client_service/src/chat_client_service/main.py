"""FastAPI service for chat client."""
import os

import slack_client_impl  # noqa: F401
from chat_client_api.client import get_client
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

app = FastAPI(
    title="Chat Client Service",
    description="Slack chat client service API",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Status ok

    """
    return {"status": "ok"}


@app.get("/auth/login")
def auth_login() -> RedirectResponse:
    """Redirect to Slack OAuth login.

    Returns:
        Redirect to Slack auth URL

    """
    client_id = os.getenv("SLACK_CLIENT_ID", "")
    redirect_uri = os.getenv(
        "SLACK_REDIRECT_URI",
        "http://localhost:8000/auth/callback",
    )
    slack_auth_url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={client_id}"
        f"&scope=chat:write,channels:read,channels:history"
        f"&redirect_uri={redirect_uri}"
    )
    return RedirectResponse(url=slack_auth_url)


@app.get("/auth/callback")
def auth_callback(code: str = "") -> dict[str, str]:
    """Handle OAuth callback from Slack.

    Args:
        code: Authorization code from Slack

    Returns:
        Success message

    """
    if not code:
        return {"error": "No code provided"}
    return {"status": "ok", "message": "Authentication successful"}


@app.get("/channels")
def list_channels() -> dict[str, list[dict[str, str | bool]]]:
    """List all Slack channels.

    Returns:
        List of channels

    """
    client = get_client()
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
    channel: str,
    text: str,
) -> dict[str, str | bool]:
    """Send a message to a Slack channel.

    Args:
        channel: Channel ID or name
        text: Message text

    Returns:
        SendMessageResponse details

    """
    client = get_client()
    response = client.send_message(channel=channel, text=text)
    return {
        "message_id": response.message_id,
        "channel": response.channel,
        "timestamp": response.timestamp,
        "ok": response.ok,
    }


@app.get("/messages")
def get_messages(
    channel: str,
    limit: int = 10,
    cursor: str = "",
) -> dict[str, list[dict[str, str]]]:
    """Get messages from a Slack channel.

    Args:
        channel: Channel ID or name
        limit: Max messages to return
        cursor: Pagination cursor

    Returns:
        List of messages

    """
    client = get_client()
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
