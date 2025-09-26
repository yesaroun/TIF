# ============================================================================
# Controller Manager
# ============================================================================

class ControllerManager:
    """
    Kubernetes Controller Manager simulation

    Controller Manager는 어러 컨트롤러를 실행하고 관리한다.
    각 컨트롤러는 독립적으로 실행되며 자신만의 리소스를 관리한다.
    """

    def __init__(self):
        self.replica_sets = {}
