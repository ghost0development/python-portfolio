from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid
import asyncio
import random
from datetime import datetime, timezone

router = APIRouter(tags=["queue"])

class Task(BaseModel):
    id: str
    name: str
    task_type: str
    status: str
    progress: int
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

class TaskCreate(BaseModel):
    name: str
    task_type: str = "generic"
    data: Optional[Dict] = None

tasks: Dict[str, Task] = {}
cancelled: set = set()

TASK_HANDLERS = {
    "email": {
        "name": "Email Campaign",
        "steps": [
            (10, "Przygotowanie listy adresatów..."),
            (25, "Renderowanie szablonu..."),
            (40, "Wysyłanie (10%)..."),
            (55, "Wysyłanie (50%)..."),
            (70, "Wysyłanie (90%)..."),
            (85, "Sprawdzanie dostarczalności..."),
            (100, "Gotowe!"),
        ],
        "result": lambda: f"Wysłano {random.randint(50, 500)} e-maili, współczynnik otwarć {random.uniform(0.15, 0.45):.1%}"
    },
    "report": {
        "name": "Generowanie Raportu",
        "steps": [
            (10, "Zbieranie danych..."),
            (30, "Agregacja statystyk..."),
            (50, "Generowanie wykresów..."),
            (70, "Formatowanie PDF..."),
            (90, "Kompresja pliku..."),
            (100, "Gotowe!"),
        ],
        "result": lambda: f"Raport wygenerowany: {random.randint(100, 500)} KB, {random.randint(5, 30)} stron"
    },
    "export": {
        "name": "Eksport Danych",
        "steps": [
            (15, "Walidacja danych źródłowych..."),
            (35, "Konwersja formatu..."),
            (50, "Eksportowanie (50%)..."),
            (75, "Eksportowanie (90%)..."),
            (90, "Tworzenie archiwum..."),
            (100, "Gotowe!"),
        ],
        "result": lambda: f"Eksport zakończony: {random.randint(1, 50)} MB, {random.randint(100, 10000)} rekordów"
    },
    "generic": {
        "name": "Generic Task",
        "steps": [
            (20, "Inicjalizacja..."),
            (40, "Przetwarzanie..."),
            (60, "Przetwarzanie..."),
            (80, "Finalizacja..."),
            (100, "Gotowe!"),
        ],
        "result": lambda: "Task completed successfully"
    },
}

@router.post("/tasks", response_model=Task)
async def create_task(task_create: TaskCreate):
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    task_type = task_create.task_type if task_create.task_type in TASK_HANDLERS else "generic"
    task = Task(
        id=task_id,
        name=task_create.name or TASK_HANDLERS[task_type]["name"],
        task_type=task_type,
        status="pending",
        progress=0,
        created_at=now,
        updated_at=now
    )
    tasks[task_id] = task
    asyncio.create_task(process_task(task_id))
    return task

@router.get("/tasks", response_model=List[Task])
async def list_tasks():
    return sorted(tasks.values(), key=lambda t: t.created_at, reverse=True)

@router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks[task_id]
    if task.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(status_code=400, detail=f"Task already {task.status}")
    cancelled.add(task_id)
    task.status = "cancelled"
    task.progress = 0
    task.result = "Cancelled by user"
    task.updated_at = datetime.now(timezone.utc).isoformat()
    tasks[task_id] = task
    return {"status": "cancelled", "task_id": task_id}

@router.delete("/tasks")
async def clear_tasks():
    tasks.clear()
    cancelled.clear()
    return {"status": "cleared"}

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        while True:
            if task_id in tasks:
                task = tasks[task_id]
                await websocket.send_json(task.model_dump())
                if task.status in ["completed", "failed", "cancelled"]:
                    break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

async def process_task(task_id: str):
    if task_id not in tasks:
        return

    task = tasks[task_id]
    task.status = "processing"
    task.updated_at = datetime.now(timezone.utc).isoformat()
    tasks[task_id] = task

    handler = TASK_HANDLERS.get(task.task_type, TASK_HANDLERS["generic"])

    for step_progress, step_label in handler["steps"]:
        if task_id in cancelled:
            cancelled.discard(task_id)
            return
        await asyncio.sleep(random.uniform(0.3, 1.0))
        if task_id in cancelled:
            cancelled.discard(task_id)
            return
        task.progress = step_progress
        task.status = "processing" if step_progress < 100 else "completed"
        if step_progress == 100:
            task.result = handler["result"]()
        task.updated_at = datetime.now(timezone.utc).isoformat()
        tasks[task_id] = task

    if task_id not in cancelled:
        task.status = "completed"
        task.progress = 100
        if not task.result:
            task.result = handler["result"]()
        task.updated_at = datetime.now(timezone.utc).isoformat()
        tasks[task_id] = task

@router.get("/types")
async def get_task_types():
    return {
        "types": [
            {"id": k, "name": v["name"], "steps": len(v["steps"])}
            for k, v in TASK_HANDLERS.items()
        ]
    }

@router.get("/health")
async def queue_health():
    active = sum(1 for t in tasks.values() if t.status in ["pending", "processing"])
    return {"status": "ok", "service": "queue", "active": active, "total": len(tasks)}