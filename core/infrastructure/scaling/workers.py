"""
Async Task Worker and Job Scheduling Module
Manages task queues, worker pools, and job scheduling with support for
background jobs, scheduled tasks, and distributed task execution.
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
from threading import Thread, Lock
from collections import deque
import heapq

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


class ScheduleType(Enum):
    """Schedule types for recurring jobs."""
    ONCE = "once"
    PERIODIC = "periodic"
    CRON = "cron"
    INTERVAL = "interval"


@dataclass
class JobResult:
    """Result of job execution."""
    job_id: str
    status: JobStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    retries: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'job_id': self.job_id,
            'status': self.status.value,
            'result': self.result,
            'error': self.error,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'retries': self.retries
        }


@dataclass
class Task:
    """Async task definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    function: Optional[Callable[..., Coroutine]] = None
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_for: Optional[datetime] = None
    max_retries: int = 3
    timeout: Optional[int] = None  # seconds
    callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    tags: Set[str] = field(default_factory=set)
    
    def __lt__(self, other: 'Task') -> bool:
        """Compare tasks for priority queue sorting."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'priority': self.priority.name,
            'created_at': self.created_at.isoformat(),
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'max_retries': self.max_retries,
            'timeout': self.timeout,
            'tags': list(self.tags)
        }


@dataclass
class ScheduledJob:
    """Scheduled job definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    task: Task = field(default_factory=Task)
    schedule_type: ScheduleType = ScheduleType.ONCE
    interval_seconds: Optional[int] = None
    cron_expression: Optional[str] = None
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    enabled: bool = True
    max_runs: Optional[int] = None
    runs: int = 0
    last_result: Optional[JobResult] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'schedule_type': self.schedule_type.value,
            'interval_seconds': self.interval_seconds,
            'cron_expression': self.cron_expression,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'enabled': self.enabled,
            'max_runs': self.max_runs,
            'runs': self.runs
        }


@dataclass
class WorkerStats:
    """Worker pool statistics."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_task_duration: float = 0.0
    active_workers: int = 0
    queued_tasks: int = 0
    max_queue_size: int = 0
    total_retries: int = 0
    scheduled_jobs: int = 0
    completed_jobs: int = 0


class WorkerPool:
    """Manages a pool of async workers for task execution."""
    
    def __init__(self, num_workers: int = 4):
        """Initialize worker pool."""
        self.num_workers = num_workers
        self.queue: List[Task] = []
        self._results: Dict[str, JobResult] = {}
        self._running: Set[str] = set()
        self._lock = asyncio.Lock()
        self._tasks_event = asyncio.Event()
        self.stats = WorkerStats()
        self._stop_event = asyncio.Event()
        self._workers: Set[asyncio.Task] = set()
    
    async def start(self) -> None:
        """Start worker pool."""
        for i in range(self.num_workers):
            worker = asyncio.create_task(self._worker())
            self._workers.add(worker)
        logger.info(f"Started worker pool with {self.num_workers} workers")
    
    async def stop(self) -> None:
        """Stop worker pool gracefully."""
        self._stop_event.set()
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("Worker pool stopped")
    
    async def submit(self, task: Task) -> str:
        """Submit task to worker pool."""
        async with self._lock:
            heapq.heappush(self.queue, task)
            self.stats.queued_tasks = len(self.queue)
            self.stats.max_queue_size = max(
                self.stats.max_queue_size,
                self.stats.queued_tasks
            )
            self.stats.total_tasks += 1
        
        self._tasks_event.set()
        logger.debug(f"Submitted task {task.id}: {task.name}")
        return task.id
    
    async def submit_many(self, tasks: List[Task]) -> List[str]:
        """Submit multiple tasks."""
        task_ids = []
        for task in tasks:
            task_ids.append(await self.submit(task))
        return task_ids
    
    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> JobResult:
        """Get task result (blocking)."""
        start_time = datetime.utcnow()
        
        while task_id not in self._results:
            if timeout:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > timeout:
                    raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")
            await asyncio.sleep(0.1)
        
        return self._results[task_id]
    
    async def _worker(self) -> None:
        """Worker coroutine that executes tasks."""
        while not self._stop_event.is_set():
            task = None
            
            async with self._lock:
                if self.queue:
                    task = heapq.heappop(self.queue)
                    self.stats.active_workers += 1
                    self.stats.queued_tasks = len(self.queue)
            
            if not task:
                self._tasks_event.clear()
                try:
                    await asyncio.wait_for(self._tasks_event.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
            else:
                self._running.add(task.id)
                result = await self._execute_task(task)
                self._results[task.id] = result
                self._running.discard(task.id)
                
                async with self._lock:
                    self.stats.active_workers -= 1
                    if result.status == JobStatus.COMPLETED:
                        self.stats.completed_tasks += 1
                    else:
                        self.stats.failed_tasks += 1
    
    async def _execute_task(self, task: Task) -> JobResult:
        """Execute individual task."""
        result = JobResult(
            job_id=task.id,
            status=JobStatus.RUNNING,
            start_time=datetime.utcnow()
        )
        
        try:
            if not task.function:
                raise ValueError(f"No function specified for task {task.id}")
            
            # Wait if scheduled for future time
            if task.scheduled_for and task.scheduled_for > datetime.utcnow():
                delay = (task.scheduled_for - datetime.utcnow()).total_seconds()
                await asyncio.sleep(delay)
            
            # Execute with timeout if specified
            if task.timeout:
                result.result = await asyncio.wait_for(
                    task.function(*task.args, **task.kwargs),
                    timeout=task.timeout
                )
            else:
                result.result = await task.function(*task.args, **task.kwargs)
            
            result.status = JobStatus.COMPLETED
            
            # Call success callback
            if task.callback:
                try:
                    if asyncio.iscoroutinefunction(task.callback):
                        await task.callback(result)
                    else:
                        task.callback(result)
                except Exception as e:
                    logger.error(f"Error in callback for task {task.id}: {e}")
        
        except asyncio.TimeoutError:
            result.status = JobStatus.FAILED
            result.error = f"Task execution timeout ({task.timeout}s)"
            logger.error(f"Task {task.id} timed out")
        
        except Exception as e:
            logger.error(f"Task {task.id} execution error: {e}")
            
            # Retry logic
            if result.retries < task.max_retries:
                result.retries += 1
                result.status = JobStatus.RETRYING
                self.stats.total_retries += 1
                
                # Re-submit for retry
                retry_delay = 2 ** result.retries  # Exponential backoff
                task.scheduled_for = datetime.utcnow() + timedelta(seconds=retry_delay)
                await self.submit(task)
            else:
                result.status = JobStatus.FAILED
                result.error = str(e)
                
                # Call error callback
                if task.error_callback:
                    try:
                        if asyncio.iscoroutinefunction(task.error_callback):
                            await task.error_callback(result)
                        else:
                            task.error_callback(result)
                    except Exception as cb_error:
                        logger.error(f"Error in error_callback for task {task.id}: {cb_error}")
        
        finally:
            result.end_time = datetime.utcnow()
            result.duration_seconds = (
                result.end_time - result.start_time
            ).total_seconds()
        
        return result
    
    def get_stats(self) -> WorkerStats:
        """Get worker pool statistics."""
        return WorkerStats(
            total_tasks=self.stats.total_tasks,
            completed_tasks=self.stats.completed_tasks,
            failed_tasks=self.stats.failed_tasks,
            active_workers=self.stats.active_workers,
            queued_tasks=self.stats.queued_tasks,
            max_queue_size=self.stats.max_queue_size,
            total_retries=self.stats.total_retries
        )


class JobScheduler:
    """Manages scheduled job execution."""
    
    def __init__(self, worker_pool: WorkerPool):
        """Initialize job scheduler."""
        self.worker_pool = worker_pool
        self._jobs: Dict[str, ScheduledJob] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.stats = WorkerStats()
    
    async def start(self) -> None:
        """Start job scheduler."""
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Job scheduler started")
    
    async def stop(self) -> None:
        """Stop job scheduler."""
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Job scheduler stopped")
    
    async def schedule_job(
        self,
        job: ScheduledJob
    ) -> str:
        """Schedule a job."""
        async with self._lock:
            self._jobs[job.id] = job
            
            # Calculate first run time
            if job.schedule_type == ScheduleType.ONCE:
                job.next_run = job.next_run or datetime.utcnow()
            elif job.schedule_type == ScheduleType.INTERVAL:
                job.next_run = datetime.utcnow() + timedelta(
                    seconds=job.interval_seconds or 60
                )
            
            self.stats.scheduled_jobs += 1
        
        logger.info(f"Scheduled job {job.id}: {job.name}")
        return job.id
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel scheduled job."""
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].enabled = False
                return True
        return False
    
    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get job by ID."""
        return self._jobs.get(job_id)
    
    def get_jobs(self) -> List[ScheduledJob]:
        """Get all jobs."""
        return list(self._jobs.values())
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while True:
            try:
                async with self._lock:
                    now = datetime.utcnow()
                    jobs_to_run = [
                        job for job in self._jobs.values()
                        if job.enabled
                        and job.next_run
                        and job.next_run <= now
                        and (not job.max_runs or job.runs < job.max_runs)
                    ]
                
                for job in jobs_to_run:
                    job.last_run = datetime.utcnow()
                    job.runs += 1
                    
                    # Submit task to worker pool
                    await self.worker_pool.submit(job.task)
                    
                    # Calculate next run
                    if job.schedule_type == ScheduleType.INTERVAL:
                        job.next_run = datetime.utcnow() + timedelta(
                            seconds=job.interval_seconds or 60
                        )
                    elif job.schedule_type == ScheduleType.ONCE:
                        job.enabled = False
                        self.stats.completed_jobs += 1
                    
                    logger.debug(f"Submitted scheduled job {job.id}")
                
                await asyncio.sleep(1)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(1)


# Singleton instances
_worker_pool: Optional[WorkerPool] = None
_job_scheduler: Optional[JobScheduler] = None
_instance_lock = Lock()


async def get_worker_pool(num_workers: int = 4) -> WorkerPool:
    """Get or create worker pool singleton."""
    global _worker_pool
    
    if _worker_pool is None:
        with _instance_lock:
            if _worker_pool is None:
                _worker_pool = WorkerPool(num_workers)
                await _worker_pool.start()
    
    return _worker_pool


async def get_job_scheduler(worker_pool: Optional[WorkerPool] = None) -> JobScheduler:
    """Get or create job scheduler singleton."""
    global _job_scheduler
    
    if _job_scheduler is None:
        with _instance_lock:
            if _job_scheduler is None:
                pool = worker_pool or await get_worker_pool()
                _job_scheduler = JobScheduler(pool)
                await _job_scheduler.start()
    
    return _job_scheduler


__all__ = [
    "WorkerPool",
    "JobScheduler",
    "Task",
    "ScheduledJob",
    "JobResult",
    "JobStatus",
    "TaskPriority",
    "ScheduleType",
    "WorkerStats",
    "get_worker_pool",
    "get_job_scheduler",
]
