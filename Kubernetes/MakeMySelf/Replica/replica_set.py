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

    ReplicaSet은 지정된 수의 Pod 복제본을 유지한다.
    selector로 관리할 Pod들을 식별하고 template으로 새로운 Pod들을 생성한다.
    """
    replicas: int
    selector: Labels  # Pod 선택을 위한 라벨 셀렉터
    template: Dict[str, Any]  # 새로운 Pod 생성을 위한 템플릿
    min_ready_seconds: int = 0  # Pod가 준비 상태로 간주되기 위한 최소 시간


class ReplicaSet:
    """
    Kubernetes ReplicaSet controller implementation

    ReplicaSet은 Replication Controller의 차세대 버전으로
    더 풍부한 라벨 셀렉터를 지원한다.
    """

    def __init__(self, name: str, namespace: str = NAMESPACE):
        self.name = name
        self.namespace = namespace
        self.uid = str(uuid.uuid4())
        self.spec: Optional[ReplicaSetSpec] = None
        self._pods: Dict[PodId, Pod]
