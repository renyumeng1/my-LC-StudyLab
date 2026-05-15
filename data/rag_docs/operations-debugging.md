# Operations And Debugging

LC-StudyLab runs as a local FastAPI backend with a Vite frontend during development. End-to-end testing should verify both HTTP status and user-visible learning states.

## Backend Startup

The backend ASGI app is `backend.api.app:app`. A typical local command is:

`uv --project backend run python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000`

The backend depends on model credentials and embedding support. If model calls are slow, workflow requests can remain pending while the planner or quiz generator is waiting for the LLM.

## Frontend Startup

The frontend is a React and Vite app. A typical command is:

`npm --prefix frontend run dev -- --host 127.0.0.1`

The Vite proxy should point to `http://127.0.0.1:8000` rather than `localhost` to avoid Windows IPv4 and IPv6 ambiguity.

## Health Checks

Use `/chat/health` to verify the backend process is reachable. Use `/rag/indexes` to verify the RAG index manager can read local index metadata. Use `/workflow/start` to verify the graph can run through planning, retrieval, and quiz generation.

## Browser Checks

A complete learning flow test should confirm:

- the page shows learning materials automatically bound
- submitting a learning goal calls `/workflow/start`
- the UI enters the planning state while the backend runs
- after `quiz_generated`, the answer panel appears
- submitting answers calls `/workflow/{thread_id}/answers`
- answer review is visible before or alongside the next retry quiz

## Common Problems

If the frontend appears stuck while planning, inspect backend logs to see whether the LLM call is still running. If the answer panel never appears, confirm the workflow state contains `quiz.questions` and `current_step` is `quiz_generated` or `waiting_for_answer`.

If retrieval returns weak documents, rebuild the default index after updating `data/rag_docs`.