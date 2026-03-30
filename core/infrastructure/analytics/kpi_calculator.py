"""
KPI Calculator - Real-time KPI calculation and background job management.

Provides:
- Real-time KPI calculations
- Background job scheduling
- Continuous metric updates
- Alert generation
"""

from typing import Dict, List, Any, Optional, Callable, Awaitable
from datetime import datetime, timedelta
import logging
import asyncio
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.monitoring import logger as structured_logger, monitor


logger = logging.getLogger(__name__)


class JobFrequency(Enum):
    """Job execution frequency."""
    
    EVERY_MINUTE = "every_minute"
    EVERY_5_MINUTES = "every_5_minutes"
    EVERY_15_MINUTES = "every_15_minutes"
    EVERY_HOUR = "every_hour"
    EVERY_6_HOURS = "every_6_hours"
    DAILY = "daily"
    WEEKLY = "weekly"


class JobStatus(Enum):
    """Background job status."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobExecution:
    """Record of a job execution."""
    
    job_id: str
    job_name: str
    status: JobStatus
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    execution_count: int


class KPICalculator:
    """Calculate KPIs in real-time."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize KPI calculator.
        
        Args:
            session: Database session
        """
        self.session = session
        self.logger = logger
        self.jobs: Dict[str, JobExecution] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
    
    @monitor.timing
    async def calculate_real_time_kpis(
        self,
        company_id: str,
        metrics: List[str]
    ) -> Dict[str, Any]:
        """
        Calculate KPIs in real-time.
        
        Args:
            company_id: Company identifier
            metrics: List of metrics to calculate
            
        Returns:
            Dictionary with real-time KPI values
        """
        try:
            structured_logger.info(
                "Calculating real-time KPIs",
                {"company_id": company_id, "metric_count": len(metrics)}
            )
            
            kpis = {}
            
            for metric in metrics:
                try:
                    kpi_value = await self._calculate_metric(company_id, metric)
                    kpis[metric] = {
                        "value": kpi_value,
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": self._get_kpi_status(metric, kpi_value)
                    }
                except Exception as e:
                    self.logger.error(f"Error calculating {metric}: {e}")
                    kpis[metric] = {
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
            
            structured_logger.info(
                "Real-time KPIs calculated",
                {"company_id": company_id, "success_count": len([k for k, v in kpis.items() if "value" in v])}
            )
            
            return kpis
            
        except Exception as e:
            self.logger.error(f"Error calculating real-time KPIs: {e}")
            raise
    
    @monitor.timing
    async def schedule_background_job(
        self,
        job_name: str,
        job_func: Callable[..., Awaitable],
        frequency: JobFrequency,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None
    ) -> str:
        """
        Schedule a background job for recurring execution.
        
        Args:
            job_name: Name of the job
            job_func: Async function to execute
            frequency: Execution frequency
            args: Positional arguments for job function
            kwargs: Keyword arguments for job function
            
        Returns:
            Job ID
        """
        try:
            job_id = self._generate_job_id(job_name)
            
            structured_logger.info(
                "Scheduling background job",
                {"job_id": job_id, "job_name": job_name, "frequency": frequency.value}
            )
            
            # Create job execution record
            job_execution = JobExecution(
                job_id=job_id,
                job_name=job_name,
                status=JobStatus.PENDING,
                started_at=datetime.utcnow(),
                completed_at=None,
                duration_seconds=None,
                result=None,
                error=None,
                execution_count=0
            )
            
            self.jobs[job_id] = job_execution
            
            # Schedule task
            delay_seconds = self._get_delay_seconds(frequency)
            task = asyncio.create_task(
                self._run_job_loop(
                    job_id, job_name, job_func, delay_seconds, args or (), kwargs or {}
                )
            )
            
            self.running_tasks[job_id] = task
            
            structured_logger.info(
                "Background job scheduled",
                {"job_id": job_id, "delay_seconds": delay_seconds}
            )
            
            return job_id
            
        except Exception as e:
            self.logger.error(f"Error scheduling job: {e}")
            raise
    
    @monitor.timing
    async def execute_job_once(
        self,
        job_name: str,
        job_func: Callable[..., Awaitable],
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Execute a job one time immediately.
        
        Args:
            job_name: Name of the job
            job_func: Async function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            Job execution result
        """
        try:
            job_id = self._generate_job_id(job_name)
            start_time = datetime.utcnow()
            
            structured_logger.info(
                "Executing job once",
                {"job_id": job_id, "job_name": job_name}
            )
            
            try:
                result = await job_func(*(args or ()), **(kwargs or {}))
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                structured_logger.info(
                    "Job executed successfully",
                    {"job_id": job_id, "duration_seconds": duration}
                )
                
                return {
                    "job_id": job_id,
                    "status": JobStatus.COMPLETED.value,
                    "duration_seconds": duration,
                    "result": result
                }
                
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                structured_logger.error(
                    "Job execution failed",
                    {"job_id": job_id, "error": str(e), "duration_seconds": duration}
                )
                
                return {
                    "job_id": job_id,
                    "status": JobStatus.FAILED.value,
                    "duration_seconds": duration,
                    "error": str(e)
                }
                
        except Exception as e:
            self.logger.error(f"Error executing job: {e}")
            raise
    
    @monitor.timing
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a background job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancelled successfully
        """
        try:
            if job_id not in self.running_tasks:
                return False
            
            task = self.running_tasks[job_id]
            task.cancel()
            
            # Wait for task to be cancelled
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            del self.running_tasks[job_id]
            
            if job_id in self.jobs:
                self.jobs[job_id].status = JobStatus.CANCELLED
            
            structured_logger.info(
                "Background job cancelled",
                {"job_id": job_id}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling job: {e}")
            return False
    
    @monitor.timing
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a background job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary with job status
        """
        try:
            if job_id not in self.jobs:
                return None
            
            execution = self.jobs[job_id]
            
            return {
                "job_id": job_id,
                "job_name": execution.job_name,
                "status": execution.status.value,
                "started_at": execution.started_at.isoformat(),
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "duration_seconds": execution.duration_seconds,
                "execution_count": execution.execution_count,
                "error": execution.error
            }
            
        except Exception as e:
            self.logger.error(f"Error getting job status: {e}")
            raise
    
    # Private helper methods
    
    async def _run_job_loop(
        self,
        job_id: str,
        job_name: str,
        job_func: Callable,
        delay_seconds: float,
        args: tuple,
        kwargs: dict
    ) -> None:
        """Run job in a loop."""
        try:
            job_execution = self.jobs[job_id]
            
            while True:
                try:
                    # Update status
                    job_execution.status = JobStatus.RUNNING
                    job_execution.started_at = datetime.utcnow()
                    
                    # Execute job
                    result = await job_func(*args, **kwargs)
                    
                    # Update execution record
                    job_execution.result = result
                    job_execution.status = JobStatus.COMPLETED
                    job_execution.completed_at = datetime.utcnow()
                    job_execution.duration_seconds = (
                        job_execution.completed_at - job_execution.started_at
                    ).total_seconds()
                    job_execution.execution_count += 1
                    job_execution.error = None
                    
                    self.logger.debug(f"Job {job_id} executed successfully")
                    
                except Exception as e:
                    job_execution.status = JobStatus.FAILED
                    job_execution.error = str(e)
                    job_execution.execution_count += 1
                    
                    self.logger.error(f"Job {job_id} failed: {e}")
                
                # Wait before next execution
                await asyncio.sleep(delay_seconds)
                
        except asyncio.CancelledError:
            self.logger.info(f"Job {job_id} cancelled")
        except Exception as e:
            self.logger.error(f"Error in job loop: {e}")
    
    async def _calculate_metric(
        self,
        company_id: str,
        metric_name: str
    ) -> float:
        """Calculate a specific metric."""
        # Placeholder: Would implement actual metric calculation
        return 50.0
    
    def _get_kpi_status(self, metric_name: str, value: float) -> str:
        """Determine KPI status."""
        # Placeholder: Would implement threshold logic
        return "healthy"
    
    def _generate_job_id(self, job_name: str) -> str:
        """Generate unique job ID."""
        import uuid
        return f"{job_name}_{uuid.uuid4().hex[:8]}"
    
    def _get_delay_seconds(self, frequency: JobFrequency) -> float:
        """Get delay in seconds for frequency."""
        frequency_map = {
            JobFrequency.EVERY_MINUTE: 60,
            JobFrequency.EVERY_5_MINUTES: 300,
            JobFrequency.EVERY_15_MINUTES: 900,
            JobFrequency.EVERY_HOUR: 3600,
            JobFrequency.EVERY_6_HOURS: 21600,
            JobFrequency.DAILY: 86400,
            JobFrequency.WEEKLY: 604800,
        }
        return frequency_map.get(frequency, 3600)
    
    async def shutdown(self) -> None:
        """Shutdown all running jobs."""
        try:
            for job_id in list(self.running_tasks.keys()):
                await self.cancel_job(job_id)
            
            self.logger.info("All jobs shut down")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
