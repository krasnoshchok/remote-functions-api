import logging
import time
import threading
from typing import Any, Dict, Callable
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from models import FunctionBase, FunctionResponse, JobResult
from user_functions.test_functions import echo, add_numbers, wait, get_status

router = APIRouter(
    prefix="/routes",
    tags=["routes"]
)

# -----------------------------------------------------------------------------
# Logging setup
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


# Dispatcher map
# Add more functions here as you add them to the `user_functions` package.
DISPATCH: Dict[str, Callable] = {
    "echo": echo,
    "add_numbers": add_numbers,
    "wait": wait,
    "get_status": get_status,
}

# In-memory store for background job results.
# NOTE: This is ephemeral and will reset if the process restarts.
JOB_RESULTS: Dict[str, Dict[str, Any]] = {}
JOB_STATUS: Dict[str, str] = {}

# -----------------------------------------------------------------------------
# Concurrency Control
# -----------------------------------------------------------------------------
# Let's make sure functions are executed one by one, since some automations may require
# full resources of the pc and they should not interrupt each other
# We must ensure that only ONE
# automation task runs at a time, even if multiple API requests come in concurrently.
API_LOCK = threading.Lock()


# -----------------------------------------------------------------------------
# Background Execution Wrapper
# -----------------------------------------------------------------------------

def _execute_task(process_id: str, func_name: str, params: dict):
    """Executes the task in a background thread.

    Uses API_LOCK to ensure tasks run sequentially (FIFO), preventing collisions.

    Stores completion/status info in the in-memory job store so callers can
    query results later via the results endpoint.
    """
    logger.info("Task %s: Queued. Waiting for API Lock...", process_id)

    with API_LOCK:
        logger.info("Task %s: API Lock acquired. Starting execution of '%s'...", process_id, func_name)
        try:
            func = DISPATCH.get(func_name)
            # Invoke the core logic
            result = func(**params)
            logger.info("Task %s: Completed successfully. Result: %s", process_id, result)

            JOB_STATUS[process_id] = "completed"
            JOB_RESULTS[process_id] = {"result": result}

        except Exception as e:
            logger.exception("Task %s: Background execution failed. Error: %s", process_id, e)
            JOB_STATUS[process_id] = "failed"
            JOB_RESULTS[process_id] = {"error": str(e)}

        finally:
            logger.info("Task %s: Releasing API Lock.", process_id)


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@router.post("/functions/async", status_code=status.HTTP_202_ACCEPTED)
def run_function_async(function: FunctionBase, background_tasks: BackgroundTasks):
    """Asynchronous endpoint.

    - Accepts the request immediately.
    - Queues the automation to run in the background.
    - Safe to call multiple times; requests will line up and run one by one.

    The result will be stored in memory and can be queried via the
    `GET /routes/functions/result/{process_id}` endpoint.
    """
    # Normalize the process_id to a string so lookup works consistently.
    process_id = str(function.process_id) if function.process_id is not None else f"proc_{int(time.time())}"

    # ADD THIS LINE FOR DEBUGGING:
    # print(f"DEBUG: Received '{server.function_to_run}'. Available: {list(DISPATCH.keys())}")

    # 1. Validate function existence
    if function.function_to_run not in DISPATCH:
        # Change this line:
        logger.warning(
            f"DEBUG: Process {process_id}: Unsupported function: {function.function_to_run}. "
            f"Available: {list(DISPATCH.keys())}")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported function: {function.function_to_run}. Available: {list(DISPATCH.keys())}"
        )

    # 2. Validate params
    params = function.params or {}
    if not isinstance(params, dict):
        raise HTTPException(status_code=400, detail="`params` must be a dictionary.")

    # 3. Initialize job state
    JOB_STATUS[process_id] = "queued"
    JOB_RESULTS.pop(process_id, None)

    # 4. Add to background tasks
    # We pass the Wrapper function (_execute_task), NOT the function directly.
    background_tasks.add_task(
        _execute_task,
        process_id=process_id,
        func_name=function.function_to_run,
        params=params
    )

    logger.info("Process %s: Request accepted for background processing.", process_id)

    return {
        "message": "Job accepted. Processing in background.",
        "process_id": process_id,
        "status": "queued"
    }


@router.post("/functions", response_model=FunctionResponse, status_code=status.HTTP_201_CREATED)
def run_function_sync(function: FunctionBase):
    """
    Legacy Synchronous endpoint.
    - Waits for to finish before returning.
    - Will BLOCK other requests because it also acquires the lock.
    """
    process_id = str(function.process_id) if function.process_id is not None else "-"

    if function.function_to_run not in DISPATCH:
        raise HTTPException(status_code=400, detail=f"Unsupported: {function.function_to_run}")

    params = function.params or {}

    logger.info("Process %s: Sync request waiting for lock...", process_id)

    # We must still use the lock here so sync requests don't crash async background tasks
    with API_LOCK:
        try:
            func = DISPATCH[function.function_to_run]
            result = func(**params)
            return FunctionResponse(
                message=f"Function '{function.function_to_run}' executed successfully.",
                data={"path": result}
            )
        except Exception as exc:
            logger.exception("Process %s: Sync execution failed", process_id)
            raise HTTPException(status_code=500, detail=str(exc))


@router.get("/functions/result/{process_id}", response_model=JobResult)
def get_function_result(process_id: str):
    """Return the status/result of a previously queued async job."""

    if process_id not in JOB_STATUS:
        raise HTTPException(status_code=404, detail=f"No job found with process_id '{process_id}'")

    status_value = JOB_STATUS.get(process_id) or "unknown"
    payload = JOB_RESULTS.get(process_id, {})

    return JobResult(
        process_id=process_id,
        status=status_value,
        result=payload.get("result"),
        error=payload.get("error")
    )
