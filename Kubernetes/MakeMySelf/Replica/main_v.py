"""
Kubernetes ReplicaSet Controller Implementation
===============================================

This module implements a Kubernetes ReplicaSet controller in Python.
ReplicaSet ensures that a specified number of Pod replicas are running at all times.

Key Concepts:
- Pod: The smallest deployable unit in Kubernetes
- ReplicaSet: Controller that maintains a stable set of replica Pods
- Controller Pattern: Control loop that continuously reconciles current state to desired state
- Label Selector: Mechanism to identify and group Pods
"""

from __future__ import annotations
import asyncio
import logging
import random
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from functools import wraps
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Protocol, Final
)
from concurrent.futures import ThreadPoolExecutor

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Type definitions and constants
# ============================================================================

T = TypeVar('T')
PodID = str
ReplicaSetID = str
Labels = Dict[str, str]

# Kubernetes namespace simulation
NAMESPACE: Final[str] = "default"

# Control loop interval (seconds)
RECONCILE_INTERVAL: Final[float] = 1.0

# Pod state transition delay times (for simulation)
POD_STARTUP_TIME: Final[float] = 0.5
POD_TERMINATION_TIME: Final[float] = 0.3


# ============================================================================
# Pod states and event definitions
# ============================================================================

class PodPhase(Enum):
    """
    Defines the lifecycle phases of a Pod.

    In Kubernetes, a Pod goes through the following phases:
    - Pending: Pod has been created but not all containers have started
    - Running: All containers have been created and at least one is running
    - Succeeded: All containers have terminated successfully
    - Failed: At least one container has terminated with failure
    - Terminating: Pod is being deleted (Graceful shutdown)
    """
    PENDING = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    TERMINATING = auto()


class EventType(Enum):
    """Kubernetes event types"""
    POD_CREATED = auto()
    POD_STARTED = auto()
    POD_TERMINATED = auto()
    POD_FAILED = auto()
    REPLICA_SCALED = auto()
    RECONCILE_START = auto()
    RECONCILE_END = auto()


# ============================================================================
# Decorators and utilities
# ============================================================================

def synchronized(lock: threading.Lock) -> Callable:
    """Synchronization decorator for thread safety"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            with lock:
                return func(*args, **kwargs)
        return wrapper
    return decorator


def measure_time(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to measure function execution time"""
    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> T:
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start
            logger.debug(f"{func.__name__} took {elapsed:.4f} seconds")

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> T:
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start
            logger.debug(f"{func.__name__} took {elapsed:.4f} seconds")

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


@contextmanager
def pod_lifecycle_context(pod_name: str):
    """Context manager for Pod lifecycle management"""
    logger.info(f"Pod {pod_name} lifecycle started")
    try:
        yield
    except Exception as e:
        logger.error(f"Pod {pod_name} encountered error: {e}")
        raise
    finally:
        logger.info(f"Pod {pod_name} lifecycle ended")


# ============================================================================
# Pod implementation
# ============================================================================

@dataclass
class PodSpec:
    """
    Pod specification definition

    In Kubernetes, PodSpec defines how a Pod should run.
    We implement a simplified version here.
    """
    image: str = "nginx:latest"  # Container image
    replicas: int = 1  # Number of container replicas (within Pod)
    resources: Dict[str, Any] = field(default_factory=lambda: {
        "cpu": "100m",  # 100 millicores
        "memory": "128Mi"  # 128 megabytes
    })
    restart_policy: str = "Always"  # Always, OnFailure, Never


@dataclass
class PodMetadata:
    """Pod metadata"""
    name: str
    namespace: str = NAMESPACE
    uid: str = field(default_factory=lambda: str(uuid.uuid4()))
    labels: Labels = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    creation_timestamp: datetime = field(default_factory=datetime.now)
    owner_references: List[Dict[str, str]] = field(default_factory=list)


class Pod:
    """
    Class representing a Kubernetes Pod

    A Pod is the basic execution unit in Kubernetes that contains one or more containers.
    Containers within the same Pod share network and storage.
    """

    def __init__(
        self,
        metadata: PodMetadata,
        spec: PodSpec,
        phase: PodPhase = PodPhase.PENDING
    ):
        self.metadata = metadata
        self.spec = spec
        self._phase = phase
        self._lock = threading.RLock()
        self._conditions: List[Dict[str, Any]] = []
        self._container_statuses: List[Dict[str, Any]] = []
        self._events: List[Tuple[EventType, datetime, str]] = []

        # Record Pod initialization event
        self._record_event(EventType.POD_CREATED, "Pod created")

    @property
    def phase(self) -> PodPhase:
        """Returns the current phase of the Pod"""
        with self._lock:
            return self._phase

    @phase.setter
    def phase(self, new_phase: PodPhase) -> None:
        """Changes the Pod phase and records the event"""
        with self._lock:
            old_phase = self._phase
            self._phase = new_phase
            self._record_event(
                EventType.POD_STARTED if new_phase == PodPhase.RUNNING else EventType.POD_TERMINATED,
                f"Pod transitioned from {old_phase.name} to {new_phase.name}"
            )

    def _record_event(self, event_type: EventType, message: str) -> None:
        """Records Pod events"""
        self._events.append((event_type, datetime.now(), message))
        logger.info(f"[Pod: {self.metadata.name}] {message}")

    async def start(self) -> None:
        """
        Starts the Pod (asynchronous)

        In real Kubernetes, kubelet starts containers through the container runtime.
        We simulate it here.
        """
        if self.phase != PodPhase.PENDING:
            return

        logger.info(f"Starting Pod {self.metadata.name}")

        # Simulate container startup
        await asyncio.sleep(POD_STARTUP_TIME)

        # Randomly simulate startup failure (10% chance)
        if random.random() < 0.1:
            self.phase = PodPhase.FAILED
            self._record_event(EventType.POD_FAILED, "Failed to start containers")
        else:
            self.phase = PodPhase.RUNNING
            self._update_container_statuses("Running")

    async def terminate(self, grace_period: float = 30.0) -> None:
        """
        Terminates the Pod (Graceful shutdown)

        Kubernetes sends SIGTERM and waits for grace period before sending SIGKILL.
        """
        if self.phase in [PodPhase.SUCCEEDED, PodPhase.FAILED, PodPhase.TERMINATING]:
            return

        logger.info(f"Terminating Pod {self.metadata.name} (grace period: {grace_period}s)")
        self.phase = PodPhase.TERMINATING

        # Simulate graceful shutdown
        await asyncio.sleep(min(POD_TERMINATION_TIME, grace_period))

        self.phase = PodPhase.SUCCEEDED
        self._update_container_statuses("Terminated")

    def _update_container_statuses(self, status: str) -> None:
        """Update container status"""
        with self._lock:
            self._container_statuses = [
                {
                    "name": f"container-{i}",
                    "state": status,
                    "ready": status == "Running",
                    "restartCount": 0,
                    "image": self.spec.image
                }
                for i in range(self.spec.replicas)
            ]

    def matches_labels(self, selector: Labels) -> bool:
        """
        Check if Pod matches label selector

        Kubernetes has equality-based and set-based label selectors.
        We implement only equality-based here.
        """
        return all(
            self.metadata.labels.get(key) == value
            for key, value in selector.items()
        )

    def is_ready(self) -> bool:
        """Check if Pod is ready"""
        return self.phase == PodPhase.RUNNING and all(
            status.get("ready", False)
            for status in self._container_statuses
        )

    def __repr__(self) -> str:
        return (
            f"Pod(name={self.metadata.name}, "
            f"phase={self.phase.name}, "
            f"labels={self.metadata.labels})"
        )


# ============================================================================
# ReplicaSet implementation
# ============================================================================

@dataclass
class ReplicaSetSpec:
    """
    ReplicaSet specification

    ReplicaSet maintains a specified number of Pod replicas.
    It identifies Pods to manage with selector and creates new Pods with template.
    """
    replicas: int  # Desired number of Pod replicas
    selector: Labels  # Label selector for selecting Pods
    template: Dict[str, Any]  # Template for creating new Pods
    min_ready_seconds: int = 0  # Minimum time for a Pod to be considered ready


class ReplicaSet:
    """
    Kubernetes ReplicaSet controller implementation

    ReplicaSet is the next generation of Replication Controller,
    supporting richer label selector expressions.
    """

    def __init__(self, name: str, namespace: str = NAMESPACE):
        self.name = name
        self.namespace = namespace
        self.uid = str(uuid.uuid4())
        self.spec: Optional[ReplicaSetSpec] = None
        self._pods: Dict[PodID, Pod] = {}
        self._lock = threading.RLock()
        self._generation = 0  # For tracking spec changes
        self._observed_generation = 0  # Last generation observed by controller
        self._conditions: List[Dict[str, Any]] = []

        # Metrics collection
        self._metrics = {
            "pods_created": 0,
            "pods_deleted": 0,
            "reconcile_count": 0,
            "last_reconcile": None
        }

        logger.info(f"ReplicaSet {name} created in namespace {namespace}")

    def update_spec(self, spec: ReplicaSetSpec) -> None:
        """Update ReplicaSet spec"""
        with self._lock:
            self.spec = spec
            self._generation += 1
            logger.info(f"ReplicaSet {self.name} spec updated (generation: {self._generation})")

    @synchronized(threading.RLock())
    def get_owned_pods(self) -> List[Pod]:
        """
        Returns Pods owned by this ReplicaSet

        Kubernetes tracks ownership relationships through ownerReferences.
        """
        return [
            pod for pod in self._pods.values()
            if any(
                ref.get("uid") == self.uid
                for ref in pod.metadata.owner_references
            )
        ]

    @synchronized(threading.RLock())
    def get_matching_pods(self) -> List[Pod]:
        """Returns all Pods matching the label selector"""
        if not self.spec:
            return []

        return [
            pod for pod in self._pods.values()
            if pod.matches_labels(self.spec.selector) and
            pod.phase not in [PodPhase.SUCCEEDED, PodPhase.FAILED, PodPhase.TERMINATING]
        ]

    async def reconcile(self) -> None:
        """
        Core logic of the reconciliation loop

        Compares current state with desired state and takes necessary actions.
        This is the heart of the Kubernetes controller pattern.
        """
        if not self.spec:
            return

        with self._lock:
            self._metrics["reconcile_count"] += 1
            self._metrics["last_reconcile"] = datetime.now()

        logger.debug(f"Starting reconciliation for ReplicaSet {self.name}")

        # Check current Pod state
        current_pods = self.get_matching_pods()
        current_count = len(current_pods)
        desired_count = self.spec.replicas

        logger.info(
            f"ReplicaSet {self.name}: Current pods: {current_count}, "
            f"Desired: {desired_count}"
        )

        # Scaling decision
        if current_count < desired_count:
            # Scale up: Create additional Pods
            await self._scale_up(desired_count - current_count)
        elif current_count > desired_count:
            # Scale down: Delete excess Pods
            await self._scale_down(current_count - desired_count, current_pods)
        else:
            # Desired state achieved
            logger.debug(f"ReplicaSet {self.name} is at desired state")

        # Replace failed Pods
        await self._replace_failed_pods(current_pods)

        # Update observed generation
        self._observed_generation = self._generation

    async def _scale_up(self, count: int) -> None:
        """Scale up the number of Pods"""
        logger.info(f"Scaling up ReplicaSet {self.name} by {count} pods")

        tasks = []
        for i in range(count):
            pod = self._create_pod()
            self._pods[pod.metadata.uid] = pod
            self._metrics["pods_created"] += 1

            # Start Pod asynchronously
            tasks.append(pod.start())

        # Wait for all Pods to start
        await asyncio.gather(*tasks)

    async def _scale_down(self, count: int, pods: List[Pod]) -> None:
        """Scale down the number of Pods"""
        logger.info(f"Scaling down ReplicaSet {self.name} by {count} pods")

        # Select Pods to delete (most recently created first)
        pods_to_delete = sorted(
            pods,
            key=lambda p: p.metadata.creation_timestamp,
            reverse=True
        )[:count]

        tasks = []
        for pod in pods_to_delete:
            tasks.append(pod.terminate())
            self._metrics["pods_deleted"] += 1

        # Wait for all Pods to terminate
        await asyncio.gather(*tasks)

        # Remove terminated Pods from the list
        with self._lock:
            for pod in pods_to_delete:
                self._pods.pop(pod.metadata.uid, None)

    async def _replace_failed_pods(self, pods: List[Pod]) -> None:
        """Replace failed Pods with new ones"""
        failed_pods = [p for p in pods if p.phase == PodPhase.FAILED]

        if failed_pods:
            logger.info(f"Replacing {len(failed_pods)} failed pods in ReplicaSet {self.name}")

            # Remove failed Pods
            with self._lock:
                for pod in failed_pods:
                    self._pods.pop(pod.metadata.uid, None)

            # Create new Pods
            await self._scale_up(len(failed_pods))

    def _create_pod(self) -> Pod:
        """
        Create a new Pod based on template

        Kubernetes uses Pod templates to create consistent Pods.
        """
        pod_name = f"{self.name}-{uuid.uuid4().hex[:8]}"

        # Copy labels from template (to match ReplicaSet selector)
        labels = self.spec.template.get("labels", {}).copy()
        labels.update(self.spec.selector)

        # Create Pod metadata
        metadata = PodMetadata(
            name=pod_name,
            namespace=self.namespace,
            labels=labels,
            annotations=self.spec.template.get("annotations", {}),
            owner_references=[{
                "apiVersion": "apps/v1",
                "kind": "ReplicaSet",
                "name": self.name,
                "uid": self.uid,
                "controller": "true",
                "blockOwnerDeletion": "true"
            }]
        )

        # Create Pod spec
        spec = PodSpec(**self.spec.template.get("spec", {}))

        pod = Pod(metadata, spec)
        logger.info(f"Created Pod {pod_name} for ReplicaSet {self.name}")

        return pod

    def get_status(self) -> Dict[str, Any]:
        """Return current status of the ReplicaSet"""
        matching_pods = self.get_matching_pods()
        ready_pods = [p for p in matching_pods if p.is_ready()]

        return {
            "replicas": len(matching_pods),
            "fullyLabeledReplicas": len(matching_pods),
            "readyReplicas": len(ready_pods),
            "availableReplicas": len(ready_pods),
            "observedGeneration": self._observed_generation,
            "conditions": self._conditions,
            "metrics": self._metrics.copy()
        }


# ============================================================================
# Controller Manager
# ============================================================================

class ControllerManager:
    """
    Kubernetes Controller Manager simulation

    Controller Manager runs and manages multiple controllers.
    Each controller runs independently and manages its own resources.
    """

    def __init__(self, worker_threads: int = 4):
        self.replica_sets: Dict[ReplicaSetID, ReplicaSet] = {}
        self._running = False
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=worker_threads)
        self._tasks: List[asyncio.Task] = []

        logger.info(f"ControllerManager initialized with {worker_threads} worker threads")

    def create_replica_set(
        self,
        name: str,
        replicas: int,
        selector: Labels,
        pod_template: Dict[str, Any]
    ) -> ReplicaSet:
        """Create a new ReplicaSet"""
        with self._lock:
            if name in self.replica_sets:
                raise ValueError(f"ReplicaSet {name} already exists")

            rs = ReplicaSet(name)
            spec = ReplicaSetSpec(
                replicas=replicas,
                selector=selector,
                template=pod_template
            )
            rs.update_spec(spec)

            self.replica_sets[name] = rs
            logger.info(f"Created ReplicaSet {name} with {replicas} replicas")

            return rs

    async def run(self) -> None:
        """Run the Controller Manager"""
        self._running = True
        logger.info("Starting ControllerManager")

        try:
            while self._running:
                # Run reconciliation for all ReplicaSets
                tasks = [
                    self._reconcile_replica_set(rs)
                    for rs in self.replica_sets.values()
                ]

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                # Wait until next reconciliation cycle
                await asyncio.sleep(RECONCILE_INTERVAL)

        except Exception as e:
            logger.error(f"ControllerManager error: {e}")
            raise
        finally:
            logger.info("ControllerManager stopped")

    async def _reconcile_replica_set(self, replica_set: ReplicaSet) -> None:
        """Reconcile individual ReplicaSet"""
        try:
            await replica_set.reconcile()
        except Exception as e:
            logger.error(f"Error reconciling ReplicaSet {replica_set.name}: {e}")

    def stop(self) -> None:
        """Stop the Controller Manager"""
        self._running = False
        self._executor.shutdown(wait=True)
        logger.info("ControllerManager shutdown complete")

    def get_cluster_status(self) -> Dict[str, Any]:
        """Return overall cluster status"""
        total_pods = 0
        ready_pods = 0

        replica_set_statuses = {}
        for name, rs in self.replica_sets.items():
            status = rs.get_status()
            replica_set_statuses[name] = status
            total_pods += status["replicas"]
            ready_pods += status.get("readyReplicas", 0)

        return {
            "replicaSets": len(self.replica_sets),
            "totalPods": total_pods,
            "readyPods": ready_pods,
            "replicaSetStatuses": replica_set_statuses
        }


# ============================================================================
# Simulation and Demo
# ============================================================================

class ChaosMonkey:
    """
    Chaos Engineering Simulator

    Randomly fails Pods to test ReplicaSet's self-healing capability.
    """

    def __init__(self, failure_rate: float = 0.1):
        self.failure_rate = failure_rate
        self._enabled = False

    async def run(self, replica_set: ReplicaSet) -> None:
        """Run Chaos Monkey"""
        while self._enabled:
            await asyncio.sleep(random.uniform(5, 10))

            if random.random() < self.failure_rate:
                pods = replica_set.get_matching_pods()
                if pods:
                    victim = random.choice(pods)
                    logger.warning(f"ChaosMonkey: Killing pod {victim.metadata.name}")
                    victim.phase = PodPhase.FAILED

    def enable(self) -> None:
        """Enable Chaos Monkey"""
        self._enabled = True
        logger.info("ChaosMonkey enabled")

    def disable(self) -> None:
        """Disable Chaos Monkey"""
        self._enabled = False
        logger.info("ChaosMonkey disabled")


async def simulate_load_balancing(replica_set: ReplicaSet) -> None:
    """
    Load balancing simulation

    In real Kubernetes, Service and Ingress handle this role.
    """
    request_count = 0

    while True:
        await asyncio.sleep(0.5)

        # Select ready Pods
        ready_pods = [
            p for p in replica_set.get_matching_pods()
            if p.is_ready()
        ]

        if ready_pods:
            # Select Pod using round-robin
            selected_pod = ready_pods[request_count % len(ready_pods)]
            logger.debug(f"Request {request_count} routed to {selected_pod.metadata.name}")
            request_count += 1


async def demo_replica_set() -> None:
    """
    ReplicaSet Demo

    Demonstrates key features of ReplicaSet:
    1. Initial Pod creation
    2. Self-healing
    3. Scaling
    4. Rolling updates
    """
    print("\n" + "="*60)
    print("Kubernetes ReplicaSet Controller Demo")
    print("="*60 + "\n")

    # Create Controller Manager
    manager = ControllerManager(worker_threads=2)

    # Create ReplicaSet
    labels = {"app": "nginx", "tier": "frontend"}
    pod_template = {
        "labels": labels,
        "spec": {
            "image": "nginx:1.21",
            "replicas": 1,
            "resources": {
                "cpu": "100m",
                "memory": "128Mi"
            }
        }
    }

    print("1. Creating ReplicaSet (replica=3)")
    rs = manager.create_replica_set(
        name="nginx-frontend",
        replicas=3,
        selector=labels,
        pod_template=pod_template
    )

    # Setup Chaos Monkey (optional)
    chaos = ChaosMonkey(failure_rate=0.2)

    # Run controller
    controller_task = asyncio.create_task(manager.run())

    # Run simulation
    try:
        # Check initial state
        await asyncio.sleep(2)
        status = manager.get_cluster_status()
        print(f"\nInitial state: {status['totalPods']} pods (Ready: {status['readyPods']})")

        # Scale up test
        print("\n2. Scaling up: replica=5")
        rs.spec.replicas = 5
        await asyncio.sleep(3)
        status = manager.get_cluster_status()
        print(f"After scale up: {status['totalPods']} pods (Ready: {status['readyPods']})")

        # Chaos test
        print("\n3. Enabling Chaos Monkey (random Pod failures)")
        chaos.enable()
        chaos_task = asyncio.create_task(chaos.run(rs))
        await asyncio.sleep(5)
        chaos.disable()
        print("Chaos Monkey disabled - checking self-healing")
        await asyncio.sleep(3)
        status = manager.get_cluster_status()
        print(f"After self-healing: {status['totalPods']} pods (Ready: {status['readyPods']})")

        # Scale down test
        print("\n4. Scaling down: replica=2")
        rs.spec.replicas = 2
        await asyncio.sleep(3)
        status = manager.get_cluster_status()
        print(f"After scale down: {status['totalPods']} pods (Ready: {status['readyPods']})")

        # Final state
        print("\n5. Final cluster state:")
        final_status = manager.get_cluster_status()
        for rs_name, rs_status in final_status["replicaSetStatuses"].items():
            print(f"  - ReplicaSet {rs_name}:")
            print(f"    * Desired: {rs.spec.replicas}")
            print(f"    * Current: {rs_status['replicas']}")
            print(f"    * Ready: {rs_status['readyReplicas']}")
            print(f"    * Metrics: {rs_status['metrics']}")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted")
    finally:
        # Cleanup
        manager.stop()
        controller_task.cancel()
        try:
            await controller_task
        except asyncio.CancelledError:
            pass


# ============================================================================
# Main execution
# ============================================================================

def main() -> None:
    """Main execution function"""
    # Run event loop
    try:
        asyncio.run(demo_replica_set())
    except KeyboardInterrupt:
        print("\nProgram terminated")
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        raise


if __name__ == "__main__":
    main()