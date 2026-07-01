# app/core/task_queue.py
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger("eppne.task_queue")

class MockTaskQueue:
    def enqueue(
        self, 
        task_name: str, 
        args: Optional[List[Any]] = None, 
        kwargs: Optional[Dict[str, Any]] = None, 
        queue: str = "default"
    ):
        logger.info(f"Task '{task_name}' queued in '{queue}' with args: {args}")

task_queue = MockTaskQueue()