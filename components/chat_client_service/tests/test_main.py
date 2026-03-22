"""Tests for the chat client FastAPI service."""

from __future__ import annotations

import os
from unittest import mock
from urllib.parse import parse_qs, urlparse

from chat_client_api.client import Channel, Message, SendMessageResponse
from chat_client_service.main import _session_store, app, reset_service_state
from fastapi.testclient import TestClient

HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_302_FOUND = 302
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_404_NOT_FOUND = 404

client = TestClient(app)


def setup_function() -> None:
    """Reset in-memory service state before each test."""
    reset_service_state()


def _create_authenticated_session() -> str:
    session = _session_store.create_session()
    test_bot_token = "xoxb-test-token"
    _session_store.authenticate_session(
        session_id=session.session_id,
        slack_bot_token=test_bot_token,
        team_name="OSPSD",
    )
    return session.session_id


def test_health() -> None:
    """Health endpoint should return an ok payload."""
    response = client.get("/health")
    assert response.status_code == HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_create_auth_session() -> None:
    """Creating an auth session should return a session token and URLs."""
    with mock.patch.dict(
        os.environ,
        {"CHAT_CLIENT_SERVICE_BASE_URL": "http://testserver"},
        clear=False,
    ):
        response = client.post("/auth/sessions")

    assert response.status_code == HTTP_201_CREATED
    data = response.json()
    assert data["authenticated"] is False
    assert data["session_id"]
    assert data["login_url"].endswith(f"/auth/login?session_id={data['session_id']}")
    assert data["status_url"].endswith(f"/auth/sessions/{data['session_id']}")


def test_auth_login_redirects_to_slack() -> None:
    """Auth login should redirect to Slack with state and redirect_uri."""
    with mock.patch.dict(
        os.environ,
        {
            "CHAT_CLIENT_SERVICE_BASE_URL": "http://testserver",
            "SLACK_CLIENT_ID": "test-client-id",
            "SLACK_REDIRECT_URI": "http://testserver/auth/callback",
        },
        clear=False,
    ):
        session_id = client.post("/auth/sessions").json()["session_id"]
        response = client.get(
            "/auth/login",
            params={"session_id": session_id},
            follow_redirects=False,
        )

    assert response.status_code == HTTP_302_FOUND
    location = response.headers["location"]
    parsed = urlparse(location)
    params = parse_qs(parsed.query)

    assert parsed.netloc == "slack.com"
    assert params["client_id"] == ["test-client-id"]
    assert params["redirect_uri"] == ["http://testserver/auth/callback"]
    assert params["state"]


def test_auth_callback_requires_code() -> None:
    """Auth callback should fail if Slack does not send a code."""
    response = client.get("/auth/callback")
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "No code provided."


def test_auth_callback_authenticates_session() -> None:
    """Auth callback should exchange the Slack code and mark the session ready."""
    with mock.patch.dict(
        os.environ,
        {
            "CHAT_CLIENT_SERVICE_BASE_URL": "http://testserver",
            "SLACK_CLIENT_ID": "test-client-id",
            "SLACK_CLIENT_SECRET": "test-client-secret",
            "SLACK_REDIRECT_URI": "http://testserver/auth/callback",
        },
        clear=False,
    ):
        session_id = client.post("/auth/sessions").json()["session_id"]
        login_response = client.get(
            "/auth/login",
            params={"session_id": session_id},
            follow_redirects=False,
        )
        state = parse_qs(urlparse(login_response.headers["location"]).query)["state"][0]

        token_response = mock.MagicMock()
        token_response.raise_for_status.return_value = None
        token_response.json.return_value = {
            "ok": True,
            "access_token": "xoxb-slack-oauth-token",
            "team": {"name": "OSPSD Team 9"},
        }

        with mock.patch(
            "chat_client_service.main.httpx.Client.post",
            return_value=token_response,
        ):
            callback_response = client.get(
                "/auth/callback",
                params={"code": "oauth-code", "state": state},
            )

    assert callback_response.status_code == HTTP_200_OK
    assert callback_response.json()["status"] == "ok"

    status_response = client.get(f"/auth/sessions/{session_id}")
    assert status_response.status_code == HTTP_200_OK
    assert status_response.json() == {
        "session_id": session_id,
        "authenticated": True,
        "team_name": "OSPSD Team 9",
    }


def test_delete_auth_session_clears_state() -> None:
    """Deleting an auth session should remove it from the store."""
    session_id = _create_authenticated_session()

    response = client.delete(f"/auth/sessions/{session_id}")
    assert response.status_code == HTTP_200_OK
    assert response.json() == {"status": "ok"}

    status_response = client.get(f"/auth/sessions/{session_id}")
    assert status_response.status_code == HTTP_404_NOT_FOUND


def test_list_channels_requires_authenticated_session() -> None:
    """List channels should reject requests without a session header."""
    response = client.get("/channels")
    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "X-Session-ID header is required."


def test_list_channels() -> None:
    """List channels should serialize channel DTOs from the concrete client."""
    session_id = _create_authenticated_session()
    mock_client = mock.MagicMock()
    mock_client.list_channels.return_value = [
        Channel(
            channel_id="C001",
            name="general",
            is_private=False,
        ),
    ]

    with mock.patch(
        "chat_client_service.main.build_chat_client",
        return_value=mock_client,
    ):
        response = client.get("/channels", headers={"X-Session-ID": session_id})

    assert response.status_code == HTTP_200_OK
    assert response.json() == {
        "channels": [
            {
                "channel_id": "C001",
                "name": "general",
                "is_private": False,
            },
        ],
    }


def test_send_message() -> None:
    """Send message should forward the JSON body to the chat client."""
    session_id = _create_authenticated_session()
    mock_client = mock.MagicMock()
    mock_client.send_message.return_value = SendMessageResponse(
        message_id="123",
        channel="C001",
        timestamp="12345.678",
        ok=True,
    )

    with mock.patch(
        "chat_client_service.main.build_chat_client",
        return_value=mock_client,
    ):
        response = client.post(
            "/messages",
            headers={"X-Session-ID": session_id},
            json={"channel": "C001", "text": "Hello from service"},
        )

    assert response.status_code == HTTP_200_OK
    assert response.json() == {
        "message_id": "123",
        "channel": "C001",
        "timestamp": "12345.678",
        "ok": True,
    }


def test_get_messages() -> None:
    """Get messages should serialize message DTOs from the chat client."""
    session_id = _create_authenticated_session()
    mock_client = mock.MagicMock()
    mock_client.get_messages.return_value = [
        Message(
            message_id="123",
            channel="C001",
            text="Hello",
            sender="U001",
            timestamp="12345.678",
        ),
    ]

    with mock.patch(
        "chat_client_service.main.build_chat_client",
        return_value=mock_client,
    ):
        response = client.get(
            "/messages",
            headers={"X-Session-ID": session_id},
            params={"channel": "C001", "limit": 5},
        )

    assert response.status_code == HTTP_200_OK
    assert response.json() == {
        "messages": [
            {
                "message_id": "123",
                "channel": "C001",
                "text": "Hello",
                "sender": "U001",
                "timestamp": "12345.678",
            },
        ],
    }
