# ============================================================================
# Pod implementation
# ============================================================================
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Any

from .main import NAMESPACE, Labels


class PodPhase(Enum):
    """
    Pod의 생애주기 정의
    https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/

    쿠버네티스에서 Pod는 다음 단계를 거친다.
    - Pending: Pod는 생성이 되었으나, 아직 실행되기 전 단계
    - Running: 모든 컨테이너가 생성되었고 적어도 한개는 실행 중인 단계
    - Succeeded: 모든 컨테이너가 성공적으로 종료된 단계
    - Failed: 1개의 Pod라도 종료에 실패한 단계
    - Terminating: Pod가 정상적으로 종료되고 삭제되고 있는 단계
    """
    PENDING = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    TERMINATING = auto()


@dataclass
class PodSpec:
    """
    Pod specification definition

    쿠버네티스에서 PodSpec은 어떻게 Pod가 실행되어야 하는지 정의한다.
    이 코드에서는 간단하게 구현한다.
    """
    image: str = "nginx:latest"
    replicas: int = 1
    resources: Dict[str, Any] = field(default_factory=lambda: {"cpu": "100m", "memory": "128Mi"})
    restart_policy: str = "Always"  # Always, OnFailure, Never


@dataclass
class PodMetadata:
    name: str
    namespace: str = NAMESPACE
    uid: str = field(default_factory=lambda: str(uuid.uuid4()))
    labels: Labels = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    # annotation은 리소스에 메타데이터를 추가하는 key-value 쌍이다. 리소스에 대한 추가 정보를 저장하고 싶을때 사용한다.
    creation_timestamp: datetime = field(default_factory=datetime.now)
    owner_references: List[Dict[str, str]] = field(default_factory=list)
    # owner_references는 Kubernetes에서 리소스 간의 소유권 관계를 나타내는 메타데이터이다.
    # 일반적으로 직접 작성하지는 않는다.
    # 리소스 생명주기를 자동으로 관리하고, '부모가 사라지면 자식도 정리'하는 메커니즘을 제공한다.


class Pod:
    """
    Class representing a Kubernetes Pod

    Pod는 하나 이상의 컨테이너를 포함하는 Kubernetes의 기본 실행 단위이다.
    같은 Pod 내의 컨테이너들은 네트워크와 스토리지를 공유한다.
    """

    def __init__(self, metadata: PodMetadata, spec: PodSpec):
        pass
