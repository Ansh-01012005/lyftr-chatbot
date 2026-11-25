# Lyftr AI Chat

A small React and FastAPI chatbot with SQLite history, LiteLLM key failover, and response caching.

## Live URLs

- Frontend: https://ansh-01012005.github.io/lyftr-chatbot/
- Backend: not deployed yet

The frontend is deployed to GitHub Pages as a static Vite build. GitHub Pages cannot host the FastAPI backend, so chat requests need a separately hosted backend URL. Set the repository variable `VITE_API_BASE_URL` to that public backend URL and re-run the Pages workflow. Until then, the deployed UI runs in browser-only demo mode so the interface remains usable without a backend; local development still uses the FastAPI API.

The local app is available at `http://localhost:3000` and `http://localhost:8000` after starting Docker. A public deployment still needs hosting accounts and real provider keys.

## Run locally: with Docker and without

### With Docker

Docker Compose uses an offline demo model by default, so the UI and API work without an API key:

```sh
make up
```

Open `http://localhost:3000`. Stop the app with `make down`. SQLite data stays in the named `chat-data` volume.

To use a real model, copy `.env.example` to `.env`, add two valid API keys, and keep `LLM_MODE=litellm`:

```sh
cp .env.example .env
```

Then run `make up` again. The included example uses Gemini. Set `LLM_MODEL` to another LiteLLM model if needed.

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

- LiteLLM mode tries configured keys in order. A failed key is skipped and the next key is tried.
- A small in-memory response cache uses the model and complete prompt history as its key. LiteLLM's local cache is also enabled for live calls.
- SQLite stores sessions and messages. A failed provider request is not saved.
- The default Docker configuration uses an offline demo reply so the project can be tried without secrets. Real model calls need two valid keys.

## Verification: how to see failover, cache hits and per-message token usage

Run the backend tests with `make test`.

- Send the same first message in two new sessions. The second response should show `LLM_CACHE`.
- Send a different message to see `LIVE_INFERENCE` (or the demo model's live result).
- With `ENABLE_FAILURE_SIMULATION=true`, send `X-Simulate-Failure: key_1=429` to `/chat`. It should answer with `key_2` and `fallback_attempts: 1`.
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
