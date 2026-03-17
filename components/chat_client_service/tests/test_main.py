"""Tests for chat client service."""
import os
from unittest import mock

from chat_client_service.main import app
from fastapi.testclient import TestClient

HTTP_200_OK = 200
HTTP_REDIRECT = (302, 307)

client = TestClient(app)


def test_health() -> None:
    """Test health endpoint returns ok."""
    response = client.get("/health")
    assert response.status_code == HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_list_channels() -> None:
    """Test list channels endpoint."""
    from chat_client_api.client import Channel
    mock_channels = [
        Channel(
            channel_id="C001",
            name="general",
            is_private=False,
        ),
    ]
    with mock.patch(
        "chat_client_service.main.get_client",
    ) as mock_get_client:
        mock_client = mock.MagicMock()
        mock_client.list_channels.return_value = mock_channels
        mock_get_client.return_value = mock_client
        response = client.get("/channels")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert len(data["channels"]) == 1
        assert data["channels"][0]["name"] == "general"


def test_send_message() -> None:
    """Test send message endpoint."""
    from chat_client_api.client import SendMessageResponse
    mock_response = SendMessageResponse(
        message_id="123",
        channel="general",
        timestamp="12345.678",
        ok=True,
    )
    with mock.patch(
        "chat_client_service.main.get_client",
    ) as mock_get_client:
        mock_client = mock.MagicMock()
        mock_client.send_message.return_value = mock_response
        mock_get_client.return_value = mock_client
        response = client.post(
            "/messages",
            params={
                "channel": "general",
                "text": "Hello!",
            },
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["ok"] is True


def test_get_messages() -> None:
    """Test get messages endpoint."""
    from chat_client_api.client import Message
    mock_messages = [
        Message(
            message_id="123",
            channel="general",
            text="Hello",
            sender="U001",
            timestamp="12345.678",
        ),
    ]
    with mock.patch(
        "chat_client_service.main.get_client",
    ) as mock_get_client:
        mock_client = mock.MagicMock()
        mock_client.get_messages.return_value = mock_messages
        mock_get_client.return_value = mock_client
        response = client.get(
            "/messages",
            params={"channel": "general"},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert len(data["messages"]) == 1
        assert data["messages"][0]["text"] == "Hello"


def test_auth_login() -> None:
    """Test auth login redirects to Slack."""
    with mock.patch.dict(
        os.environ,
        {"SLACK_CLIENT_ID": "test-client-id"},
    ):
        response = client.get(
            "/auth/login",
            follow_redirects=False,
        )
        assert response.status_code in HTTP_REDIRECT


def test_auth_callback_no_code() -> None:
    """Test auth callback with no code."""
    response = client.get("/auth/callback")
    assert response.status_code == HTTP_200_OK
    data = response.json()
    assert "error" in data
