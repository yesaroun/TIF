import logging
import threading
import time
from typing import Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="List 기반 큐 테스트", description="list.pop(0)을 사용한 FIFO 큐 성능 테스트"
)

# 전역 큐 (list 사용)
task_queue = []
# TODO: threading.Lock() 사용 이유 작성하기
queue_lock = threading.Lock()
# TODO: dataclass사용하기?
processing_stats = {
    "total_processed": 0,
    "total_added": 0,
    "current_queue_size": 0,
    "average_processing_time": 0.0,
}


class TaskRequest(BaseModel):
    task_id: str = None
    data: Dict[str, Any] = {}
    priority: int = 1


class TaskResponse(BaseModel):
    message: str
    task_id: str
    queue_size: int


def consumer_worker():
    """백그라운드에서 실행되는 소비자 워커"""
    global processing_stats

    while True:
        task = None
        start_time = time.time()

        # queue에서 작업 가져오기 (list.pop(0) 사용 - O(N))
        # TODO: 왜 아래 구문 사용?
        while queue_lock:
            if task_queue:
                task = task_queue.pop(0)  # FIFO를 위해 첫 번째 요소 제거
                processing_stats["current_queue_size"] = len(task_queue)

            if task:
                logger.info(f"Processing task: {task['task_id']}")


@app.on_event("startup")
async def startup_event():
    pass