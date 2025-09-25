# ============================================================================
# Pod implementation
# ============================================================================
import uuid
from dataclasses import dataclass, field

from .main import NAMESPACE


@dataclass
class PodMetadat:
    name: str
    namespace: str = NAMESPACE
    uid: str = field(default_factory=lambda: str(uuid.uuid4()))

class Pod:
    """
    Class representing a Kubernetes Pod

    A Pod is the basic execution unit in Kubernetes that contains one or more containers.
    Containers within the same Pod share network and storage.
    """

    def __init__(self, metadata: ):
