"""CI/CD pipeline and deployment automation.

Provides deployment automation, health checks, rollback mechanisms,
and deployment monitoring.
"""

import logging
import threading
import subprocess
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Callable, Any
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


class DeploymentStatus(str, Enum):
    """Deployment status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentStage(str, Enum):
    """Deployment stages."""

    BUILD = "build"
    TEST = "test"
    SECURITY_SCAN = "security_scan"
    STAGING_DEPLOY = "staging_deploy"
    STAGING_TEST = "staging_test"
    PRODUCTION_DEPLOY = "production_deploy"
    PRODUCTION_VERIFY = "production_verify"
    CLEANUP = "cleanup"


@dataclass
class StageResult:
    """Result of deployment stage."""

    stage: DeploymentStage
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    output: str = ""
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "output": self.output,
            "error_message": self.error_message,
            "details": self.details,
        }


@dataclass
class Deployment:
    """Deployment record."""

    deployment_id: str
    version: str
    environment: str
    triggered_at: datetime
    triggered_by: str
    status: DeploymentStatus = DeploymentStatus.PENDING
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    stages: List[StageResult] = field(default_factory=list)
    rollback_needed: bool = False
    rollback_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "deployment_id": self.deployment_id,
            "version": self.version,
            "environment": self.environment,
            "triggered_at": self.triggered_at.isoformat(),
            "triggered_by": self.triggered_by,
            "status": self.status.value,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "stages": [s.to_dict() for s in self.stages],
            "rollback_needed": self.rollback_needed,
            "rollback_version": self.rollback_version,
        }


class PipelineStep:
    """Single pipeline step."""

    def __init__(
        self,
        name: str,
        stage: DeploymentStage,
        command: str,
        timeout_seconds: int = 300,
    ):
        """Initialize pipeline step.

        Args:
            name: Step name
            stage: Deployment stage
            command: Command to execute
            timeout_seconds: Command timeout
        """
        self.name = name
        self.stage = stage
        self.command = command
        self.timeout_seconds = timeout_seconds

    def execute(self) -> tuple[bool, str, str]:
        """Execute pipeline step.

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            logger.info(f"Executing step: {self.name}")
            result = subprocess.run(
                self.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )

            success = result.returncode == 0
            if success:
                logger.info(f"Step {self.name} completed successfully")
            else:
                logger.error(f"Step {self.name} failed: {result.stderr}")

            return success, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Step {self.name} timed out after {self.timeout_seconds}s")
            return False, "", f"Timeout after {self.timeout_seconds}s"
        except Exception as e:
            logger.error(f"Step {self.name} failed: {e}")
            return False, "", str(e)


class DeploymentPipeline:
    """CI/CD deployment pipeline."""

    def __init__(self):
        """Initialize deployment pipeline."""
        self.steps: List[PipelineStep] = []
        self.deployments: deque = deque(maxlen=1000)
        self.lock = threading.RLock()
        self.current_deployment: Optional[Deployment] = None

    def add_step(self, step: PipelineStep) -> None:
        """Add pipeline step.

        Args:
            step: Pipeline step
        """
        with self.lock:
            self.steps.append(step)
            logger.info(f"Added pipeline step: {step.name}")

    def trigger_deployment(
        self, deployment_id: str, version: str, environment: str, triggered_by: str
    ) -> Deployment:
        """Trigger new deployment.

        Args:
            deployment_id: Deployment ID
            version: Version to deploy
            environment: Target environment
            triggered_by: User triggering deployment

        Returns:
            Deployment record
        """
        with self.lock:
            deployment = Deployment(
                deployment_id=deployment_id,
                version=version,
                environment=environment,
                triggered_at=datetime.now(),
                triggered_by=triggered_by,
            )

            self.current_deployment = deployment
            self.deployments.append(deployment)
            logger.info(f"Triggered deployment: {deployment_id}")

            return deployment

    def execute_deployment(self, deployment: Deployment) -> bool:
        """Execute complete deployment.

        Args:
            deployment: Deployment to execute

        Returns:
            True if successful
        """
        with self.lock:
            deployment.status = DeploymentStatus.IN_PROGRESS
            start_time = time.time()

            try:
                for step in self.steps:
                    logger.info(f"Executing stage: {step.stage.value}")

                    step_start = datetime.now()
                    success, stdout, stderr = step.execute()
                    step_end = datetime.now()

                    result = StageResult(
                        stage=step.stage,
                        status=DeploymentStatus.COMPLETED if success else DeploymentStatus.FAILED,
                        started_at=step_start,
                        completed_at=step_end,
                        duration_seconds=(step_end - step_start).total_seconds(),
                        output=stdout,
                        error_message=stderr if not success else None,
                    )

                    deployment.stages.append(result)

                    if not success:
                        logger.error(f"Deployment failed at stage: {step.stage.value}")
                        deployment.status = DeploymentStatus.FAILED
                        deployment.completed_at = datetime.now()
                        deployment.duration_seconds = time.time() - start_time
                        return False

                deployment.status = DeploymentStatus.COMPLETED
                deployment.completed_at = datetime.now()
                deployment.duration_seconds = time.time() - start_time
                logger.info(f"Deployment completed successfully: {deployment.deployment_id}")
                return True

            except Exception as e:
                logger.error(f"Deployment error: {e}")
                deployment.status = DeploymentStatus.FAILED
                deployment.completed_at = datetime.now()
                deployment.duration_seconds = time.time() - start_time
                return False

    def rollback(self, deployment: Deployment, rollback_version: str) -> bool:
        """Rollback deployment.

        Args:
            deployment: Deployment to rollback
            rollback_version: Version to rollback to

        Returns:
            True if successful
        """
        with self.lock:
            logger.warning(f"Rolling back deployment {deployment.deployment_id}")

            try:
                rollback_deployment = self.trigger_deployment(
                    deployment_id=f"{deployment.deployment_id}-rollback",
                    version=rollback_version,
                    environment=deployment.environment,
                    triggered_by="system",
                )

                success = self.execute_deployment(rollback_deployment)

                if success:
                    deployment.status = DeploymentStatus.ROLLED_BACK
                    deployment.rollback_version = rollback_version
                    logger.info(f"Rollback completed: {rollback_version}")

                return success

            except Exception as e:
                logger.error(f"Rollback failed: {e}")
                return False

    def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Get deployment record.

        Args:
            deployment_id: Deployment ID

        Returns:
            Deployment record
        """
        with self.lock:
            for d in self.deployments:
                if d.deployment_id == deployment_id:
                    return d
            return None

    def get_deployments(
        self, environment: Optional[str] = None, limit: int = 100
    ) -> List[Deployment]:
        """Get deployment history.

        Args:
            environment: Filter by environment
            limit: Max deployments to return

        Returns:
            List of deployments
        """
        with self.lock:
            deployments = list(self.deployments)
            if environment:
                deployments = [d for d in deployments if d.environment == environment]
            return deployments[-limit:]


class DeploymentMonitor:
    """Monitors deployment health and metrics."""

    def __init__(self):
        """Initialize deployment monitor."""
        self.health_checks: Dict[str, Callable[[], bool]] = {}
        self.deployment_metrics: deque = deque(maxlen=10000)
        self.lock = threading.RLock()

    def register_health_check(self, name: str, check_fn: Callable[[], bool]) -> None:
        """Register health check.

        Args:
            name: Check name
            check_fn: Check function
        """
        with self.lock:
            self.health_checks[name] = check_fn
            logger.info(f"Registered health check: {name}")

    def run_health_checks(self) -> Dict[str, bool]:
        """Run all health checks.

        Returns:
            Check results
        """
        with self.lock:
            results = {}
            for name, check_fn in self.health_checks.items():
                try:
                    results[name] = check_fn()
                except Exception as e:
                    logger.error(f"Health check failed: {name}: {e}")
                    results[name] = False

            return results

    def verify_deployment(self, deployment: Deployment) -> bool:
        """Verify deployment health.

        Args:
            deployment: Deployment to verify

        Returns:
            True if healthy
        """
        with self.lock:
            checks = self.run_health_checks()
            healthy = all(checks.values())

            metrics = {
                "deployment_id": deployment.deployment_id,
                "timestamp": datetime.now().isoformat(),
                "healthy": healthy,
                "checks": checks,
            }

            self.deployment_metrics.append(metrics)

            if healthy:
                logger.info(f"Deployment verification passed: {deployment.deployment_id}")
            else:
                logger.warning(f"Deployment verification failed: {deployment.deployment_id}")
                logger.warning(f"Failed checks: {[k for k, v in checks.items() if not v]}")

            return healthy

    def get_deployment_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get deployment metrics.

        Args:
            limit: Max metrics to return

        Returns:
            List of metrics
        """
        with self.lock:
            return list(self.deployment_metrics)[-limit:]


class CanaryDeployment:
    """Manages canary deployments."""

    def __init__(self):
        """Initialize canary deployment."""
        self.active_deployments: Dict[str, float] = {}  # deployment_id -> traffic_percentage
        self.lock = threading.RLock()

    def start_canary(
        self,
        deployment_id: str,
        initial_traffic_percentage: float = 5.0,
        increment_percentage: float = 10.0,
        check_interval_seconds: int = 60,
    ) -> None:
        """Start canary deployment.

        Args:
            deployment_id: Deployment ID
            initial_traffic_percentage: Initial traffic percentage
            increment_percentage: Percentage to increment on each step
            check_interval_seconds: Interval between checks
        """
        with self.lock:
            self.active_deployments[deployment_id] = initial_traffic_percentage
            logger.info(
                f"Started canary deployment: {deployment_id} "
                f"({initial_traffic_percentage}% traffic)"
            )

    def increment_canary(self, deployment_id: str, increment: float) -> Optional[float]:
        """Increment canary traffic.

        Args:
            deployment_id: Deployment ID
            increment: Traffic increment percentage

        Returns:
            New traffic percentage
        """
        with self.lock:
            if deployment_id not in self.active_deployments:
                return None

            new_percentage = min(100, self.active_deployments[deployment_id] + increment)
            self.active_deployments[deployment_id] = new_percentage

            if new_percentage >= 100:
                logger.info(f"Canary deployment completed: {deployment_id}")
                del self.active_deployments[deployment_id]

            return new_percentage

    def get_traffic_percentage(self, deployment_id: str) -> Optional[float]:
        """Get current traffic percentage.

        Args:
            deployment_id: Deployment ID

        Returns:
            Traffic percentage
        """
        with self.lock:
            return self.active_deployments.get(deployment_id)

    def abort_canary(self, deployment_id: str) -> bool:
        """Abort canary deployment.

        Args:
            deployment_id: Deployment ID

        Returns:
            True if aborted
        """
        with self.lock:
            if deployment_id in self.active_deployments:
                del self.active_deployments[deployment_id]
                logger.warning(f"Aborted canary deployment: {deployment_id}")
                return True
            return False


# Singleton instances
_pipeline: Optional[DeploymentPipeline] = None
_monitor: Optional[DeploymentMonitor] = None
_canary: Optional[CanaryDeployment] = None


def get_deployment_pipeline() -> DeploymentPipeline:
    """Get deployment pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = DeploymentPipeline()
        logger.info("Initialized DeploymentPipeline")
    return _pipeline


def get_deployment_monitor() -> DeploymentMonitor:
    """Get deployment monitor singleton."""
    global _monitor
    if _monitor is None:
        _monitor = DeploymentMonitor()
        logger.info("Initialized DeploymentMonitor")
    return _monitor


def get_canary_deployment() -> CanaryDeployment:
    """Get canary deployment singleton."""
    global _canary
    if _canary is None:
        _canary = CanaryDeployment()
        logger.info("Initialized CanaryDeployment")
    return _canary
