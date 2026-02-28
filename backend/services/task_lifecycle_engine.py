from backend.core.enums import TaskStatus
from backend.core.exceptions import TaskExecutionError


class TaskLifecycleEngine:

    def __init__(self):
        self.valid_transitions = {
            TaskStatus.PENDING: [TaskStatus.QUEUED],
            TaskStatus.QUEUED:  [TaskStatus.RUNNING],
            TaskStatus.RUNNING: [
                TaskStatus.SUCCESS,
                TaskStatus.FAILED,
                TaskStatus.RETRYING,
            ],
            TaskStatus.RETRYING: [TaskStatus.RUNNING],
            TaskStatus.SUCCESS:  [],
            TaskStatus.FAILED:   [],
        }

    def validate_transition(self, current_status, new_status):
        allowed = self.valid_transitions.get(current_status, [])
        if new_status not in allowed:
            raise TaskExecutionError(
                f"Invalid transition: {current_status} → {new_status}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

    def is_terminal(self, status):
        return status in [TaskStatus.SUCCESS, TaskStatus.FAILED]