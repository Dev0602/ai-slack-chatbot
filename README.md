# AI Slack Chatbot

An AI-powered Slack assistant built with FastAPI, supporting natural language commands, cross-platform integrations, and real-time observability.

## Live Demo

- **Service:** https://ai-slack-chatbot.onrender.com
- **Health Check:** https://ai-slack-chatbot.onrender.com/health
- **Telemetry Dashboard:** https://ai-slack-chatbot.onrender.com/dashboard
- **Prometheus Metrics:** https://ai-slack-chatbot.onrender.com/metrics/prometheus

## About

This project is an AI-powered Slack chatbot service that allows users to interact with Slack channels using natural language. The AI understands commands like "send a message to #general" or "create a ticket for the login bug" and executes them automatically.

Built using professional software engineering practices including dependency injection, abstract interfaces, microservice architecture, Infrastructure as Code, and CI/CD pipelines.

## Architecture

The system is composed of modular components:

- `chat_client_api` — abstract `ChatClient` contract and DTOs
- `slack_client_impl` — Slack API implementation
- `chat_client_service` — FastAPI deployment unit with AI, telemetry, and Prometheus metrics
- `chat_client_service_api_client` — auto-generated OpenAPI HTTP client
- `chat_client_adapter` — remote `ChatClient` implementation over the service
- `ai_client_api` — provider-agnostic AI client interface with typed tool definitions
- `openai_ai_client_impl` — OpenAI function-calling implementation
- `anthropic_ai_client_impl` — Anthropic Claude implementation (swappable with OpenAI)
- `ticket_client_api` — abstract issue tracker contract
- `http_ticket_client_impl` — HTTP implementation for issue tracker integration

## Features

- **AI Chat Assistant** — natural language commands dispatched via OpenAI or Anthropic Claude function calling
- **Slack Integration** — send/read messages, list channels, manage conversations
- **Cross-Vertical Integration** — create and manage tickets in issue tracker systems
- **Calendar Integration** — schedule and manage events via natural language
- **Real-time Observability** — live telemetry dashboard with request latency, success/failure rates, and AI token cost tracking
- **OAuth 2.0** — secure multi-user authentication flow
- **Provider-agnostic AI** — swap between OpenAI and Anthropic Claude without code changes

## Tech Stack

- **Language:** Python 3.12+
- **Framework:** FastAPI
- **Package Manager:** uv
- **AI Providers:** OpenAI, Anthropic Claude
- **Deployment:** Render
- **IaC:** Terraform
- **CI/CD:** CircleCI
- **Observability:** Prometheus + Grafana Cloud
- **Testing:** pytest (155 tests, 92.76% coverage)
- **Code Quality:** ruff, mypy strict

## Quick Start

```bash
uv sync --all-packages
uv run ruff check .
uv run mypy .
uv run pytest --cov=components --cov-report=term-missing
```

Run the service locally:

```bash
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_CLIENT_ID="your-slack-client-id"
export SLACK_CLIENT_SECRET="your-slack-client-secret"
export SLACK_REDIRECT_URI="http://localhost:8000/auth/callback"
export ANTHROPIC_API_KEY="sk-ant-..."
export CALENDAR_DEMO_MODE="true"
uv run uvicorn chat_client_service.main:app --reload --app-dir components/chat_client_service/src
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SLACK_BOT_TOKEN` | yes | Slack Bot Token |
| `SLACK_CLIENT_ID` | yes | Slack App client ID |
| `SLACK_CLIENT_SECRET` | yes | Slack App client secret |
| `SLACK_SIGNING_SECRET` | yes | Slack signing secret |
| `ANTHROPIC_API_KEY` | yes | Anthropic Claude API key |
| `CALENDAR_DEMO_MODE` | yes | Set to `true` for demo mode |
| `OPENAI_API_KEY` | optional | OpenAI API key (alternative to Anthropic) |

## Deployment

Deployed on **Render** with Terraform IaC:

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

CI/CD via CircleCI — every push runs ruff, mypy, pytest with 90% coverage gate, and auto-deploys to Render on green builds.

## Quality Gates

- `ruff` with `select = ["ALL"]`
- `mypy` strict mode
- `pytest` — 155 tests, 92.76% coverage
- `mkdocs build --strict`

## Author

**Baireddy Devendhar Reddy**
- GitHub: [Dev0602](https://github.com/Dev0602)
- Project: [ai-slack-chatbot](https://github.com/Dev0602/ai-slack-chatbot)
