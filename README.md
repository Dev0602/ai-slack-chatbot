# Chat Client Service

HW2 implements a Slack-backed chat client as a five-component system:

- `chat_client_api`: the abstract `ChatClient` contract and DTOs.
- `slack_client_impl`: the direct Slack implementation for local use.
- `chat_client_service`: the FastAPI deployment unit with Slack OAuth and session-token auth.
- `chat_client_service_api_client`: the OpenAPI-generated HTTP client for the service.
- `chat_client_adapter`: an adapter that implements `ChatClient` by calling the remote service.

## Team

- Harshith Kori Raj
- Lakshmi Hukunda Raju
- Jahnavi Saladhagu
- Baireddy Devendhar Reddy
- Sai Krishna Kommineni

## Quick Start

```bash
uv sync --all-packages
uv run ruff check .
uv run mypy .
uv run pytest --cov=components --cov-report=term-missing
```

Run the service locally:

```bash
export CHAT_CLIENT_SERVICE_BASE_URL="http://localhost:8000"
export SLACK_CLIENT_ID="your-slack-client-id"
export SLACK_CLIENT_SECRET="your-slack-client-secret"
export SLACK_REDIRECT_URI="http://localhost:8000/auth/callback"
uv run uvicorn chat_client_service.main:app --reload
```

Use the remote adapter through the original interface:

```python
import chat_client_adapter
from chat_client_api import get_client

client = get_client()
channels = client.list_channels()
```

If `CHAT_CLIENT_SERVICE_SESSION_ID` is not set, the adapter creates a service auth session, opens the browser to Slack login, waits for the callback to complete, and then continues through the same `ChatClient` contract.

## Environment Variables

- `SLACK_BOT_TOKEN`: required only for the direct local `slack_client_impl`.
- `SLACK_CLIENT_ID`: Slack OAuth client ID for the FastAPI service.
- `SLACK_CLIENT_SECRET`: Slack OAuth client secret for the FastAPI service.
- `SLACK_REDIRECT_URI`: OAuth callback URL registered with Slack.
- `SLACK_SCOPES`: optional Slack scopes override for the service.
- `CHAT_CLIENT_SERVICE_BASE_URL`: base URL used by the service and adapter.
- `CHAT_CLIENT_SERVICE_SESSION_ID`: optional existing remote auth session.
- `CHAT_CLIENT_SERVICE_OPEN_BROWSER`: whether the adapter should open the browser automatically.
- `CHAT_CLIENT_SERVICE_AUTH_TIMEOUT_SECONDS`: how long the adapter waits for OAuth completion.
- `CHAT_CLIENT_SERVICE_POLL_INTERVAL_SECONDS`: how often the adapter polls auth status.

## Generated Client

The service client is generated from the FastAPI OpenAPI schema with `openapi-python-client`. Regenerate it with:

```bash
uv run python -c "from chat_client_service.main import app; import json, pathlib; pathlib.Path('openapi-chat-client-service.json').write_text(json.dumps(app.openapi(), indent=2), encoding='utf-8')"
uv run openapi-python-client generate --path openapi-chat-client-service.json --config openapi-python-client-config.yml --meta uv --output-path components/chat_client_service_api_client --overwrite
```

## Quality Gates

- `ruff` passes with the handwritten codebase.
- `mypy` runs in strict mode.
- `pytest --cov=components` exceeds the `90%` threshold from `pyproject.toml`.
- `mkdocs build --strict` succeeds.

## Deployment Status

The service is deployment-ready in structure: it includes `/health`, environment-driven configuration, and a service client generated from OpenAPI. Public cloud deployment, a public base URL, and automated deploy jobs are intentionally not completed in this working tree yet.
