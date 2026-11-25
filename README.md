# Lyftr AI Chat

A small React and FastAPI chatbot with SQLite history, LiteLLM model/key failover, and response caching.

## Live URLs

- Frontend: https://ansh-01012005.github.io/lyftr-chatbot/
- Backend: https://lyftr-chatbot-api-sait.onrender.com

The frontend is deployed to GitHub Pages as a static Vite build and is connected to the FastAPI backend on Render. If the `VITE_API_BASE_URL` repository variable is removed, the frontend falls back to browser-only demo mode so the interface remains usable without a backend.

The local app is available at `http://localhost:3000` and `http://localhost:8000` after starting Docker. The public deployment uses Render for the FastAPI backend and an OpenRouter key stored only in Render's environment variables.

## Run locally: with Docker and without

### With Docker

Docker Compose uses an offline demo model by default, so the UI and API work without an API key:

```sh
make up
```

Open `http://localhost:3000`. Stop the app with `make down`. SQLite data stays in the named `chat-data` volume.

To use a real model, copy `.env.example` to `.env`, add one valid OpenRouter API key, and keep `LLM_MODE=litellm`:

```sh
cp .env.example .env
```

Then run `make up` again. The included example uses OpenRouter's free Nemotron model with free fallback models. Set `LLM_MODEL` to another LiteLLM model if needed.

### Without Docker

Install the backend requirements and run the API:

```sh
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
LLM_MODE=mock LLM_API_KEYS=demo-key-1,demo-key-2 DATABASE_URL=sqlite:///./app.db uvicorn main:app --reload
```

In another terminal, start the frontend:

```sh
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Design decisions: key fallback, caching, SQLite session storage

- LiteLLM mode tries the primary free model first, then each fallback model. Failed models are skipped; if multiple keys are configured, keys are tried in order.
- A small in-memory response cache uses the model and complete prompt history as its key. LiteLLM's local cache is also enabled for live calls.
- SQLite stores sessions and messages. A failed provider request is not saved.
- The default Docker configuration uses an offline demo reply so the project can be tried without secrets. Real model calls need one valid OpenRouter key.

## Verification: how to see failover, cache hits and per-message token usage

Run the backend tests with `make test`.

- Send the same first message in two new sessions. The second response should show `LLM_CACHE`.
- Send a different message to see `LIVE_INFERENCE` (or the demo model's live result).
- With `ENABLE_FAILURE_SIMULATION=true` and two keys configured, send `X-Simulate-Failure: key_1=429` to `/chat`. It should answer with `key_2` and `fallback_attempts: 1`. With one key, leave failure simulation disabled.
- Send `X-Simulate-Failure: *=429` with a new message. The API should return `503` and leave session history unchanged.
- Each assistant reply shows that request's input and output token counts.

The API endpoints are `GET /health`, `POST /chat`, and `GET /sessions/{session_id}/messages`.

## Setup Used: your editor and AI tools

OpenCode was used to create the project. The app uses React, Vite, FastAPI, LiteLLM, and SQLite.

## Bonus features (if any): what you added beyond requirements and why

- Offline demo mode makes the app easy to run before provider credentials are available.
- The system prompt can be set from the chat UI.

## Frontend deployment

The `Deploy frontend to GitHub Pages` workflow builds `frontend/` with Vite and publishes the static bundle to GitHub Pages. It runs on pushes to `main` that change the frontend, or manually from the Actions tab.

To connect the live frontend to a hosted API, add a repository variable named `VITE_API_BASE_URL` under **Settings → Secrets and variables → Actions → Variables**, then re-run the workflow.

## Backend deployment

`render.yaml` describes a free Render Docker web service for the FastAPI backend. Create a Render Blueprint from this repository, enter the OpenRouter key when Render prompts for `LLM_API_KEYS`, and deploy. Then add the resulting service URL as the `VITE_API_BASE_URL` repository variable and re-run the Pages workflow.

Render's free instances sleep after inactivity, so the first request may be slow. SQLite data stored in `/tmp` is ephemeral on this free setup.
