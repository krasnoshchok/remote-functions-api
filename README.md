# Remote Functions API

FastAPI microservice that exposes Python functions as REST endpoints. Supports sync and async execution with job tracking, sequential locking, and structured logging. Docker-ready for Cloud Foundry deployment.

---

## Project structure

```
├── main.py                    # App entry point
├── models.py                  # Pydantic request/response models
├── logging_config.py          # Structured logging setup
├── requirements.txt
├── Dockerfile
├── routers/
│   └── routes.py              # API endpoints + job dispatcher
└── user_functions/
    └── test_functions.py      # Registered callable functions
```

---

## How it works

1. Client sends a `POST` request with the name of the function to run and its parameters.
2. The server either executes it **synchronously** (blocks until done) or **asynchronously** (returns a job ID immediately).
3. For async jobs, the client polls `GET /routes/functions/result/{process_id}` to retrieve the result.
4. All tasks share a single `threading.Lock` — jobs queue up and run one at a time.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/routes/functions` | Run a function synchronously |
| `POST` | `/routes/functions/async` | Queue a function as a background job |
| `GET` | `/routes/functions/result/{process_id}` | Get the result of a background job |

---

## Available functions

| `function_to_run` | Required `params` | Description |
|---|---|---|
| `echo` | `text: str`, `prefix?: str` | Returns text back to the caller |
| `add_numbers` | `numbers: list[float]` | Returns sum and count |
| `wait` | `seconds?: float` | Sleeps for N seconds (simulates a long job) |
| `get_status` | — | Returns a health payload with timestamp and UUID |

---

## Quick start

### Run locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Run with Docker

```bash
docker build -t listener .
docker run -e PORT=8080 -p 8080:8080 listener
```

---

## Example — async job

**1. Queue a job (server returns a job ID)**

```bash
curl -X POST http://localhost:8080/routes/functions/async \
  -H "Content-Type: application/json" \
  -d '{"function_to_run": "add_numbers", "params": {"numbers": [1, 2, 3]}}'
```

```json
{"message": "Job accepted.", "process_id": "proc_1700000000", "status": "queued"}
```

**2. Poll for the result**

```bash
curl http://localhost:8080/routes/functions/result/proc_1700000000
```

```json
{"process_id": "proc_1700000000", "status": "completed", "result": {"sum": 6.0, "count": 3}, "error": null}
```

---

## Adding a new function

1. Add your function to `user_functions/` (any `.py` file).
2. Import it in `routers/routes.py`.
3. Register it in the `DISPATCH` dict:

```python
DISPATCH: Dict[str, Callable] = {
    "my_function": my_function,
    ...
}
```

---

## Deployment — Cloud Foundry

Cloud Foundry injects `$PORT` at runtime automatically. The Dockerfile reads this variable, so no changes are needed.

```bash
cf push listener --docker-image <your-registry>/listener:latest
```

> **Note:** Job results are stored in memory. They will be lost if the instance restarts. For persistence, consider adding a database or Redis store.
