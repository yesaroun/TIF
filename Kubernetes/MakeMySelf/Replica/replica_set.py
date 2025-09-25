# ============================================================================
# ReplicaSet implementation
# ============================================================================
import uuid
from dataclasses import dataclass
from typing import Dict, Any, Optional

from .main import NAMESPACE, Labels, PodID


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
    min_ready_seconds: int = 0  # Minimum time fore a Pod to be considered ready


class ReplicaSet:
    """
    Kubernetes ReplicaSet controller implementation

    ReplicaSet is the next generation of Replication Controller
    supporting richer label selector expressions
    """

    def __init__(self, name: str, namespace: str = NAMESPACE):
        self.name = name
        self.namespace = namespace
        self.uid = str(uuid.uuid4())
        self.spec: Optional[ReplicaSetSpec] = None
        self._pods: Dict[PodId, Pod]
