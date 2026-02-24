from backend.core.enums import TaskStatus
from backend.core.exceptions import TaskExecutionError


class TaskLifecycleEngine:

    def __init__(self):
        self.valid_transitions = {
            TaskStatus.PENDING: [TaskStatus.RUNNING],
            TaskStatus.RUNNING: [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED
            ],
            TaskStatus.FAILED: [],
            TaskStatus.COMPLETED: []
        }


    def validate_transition(self, current_status, new_status):

        if new_status not in self.valid_transitions.get(current_status, []):
            raise TaskExecutionError(
                f"Invalid transition {current_status} → {new_status}"
            )


    def is_terminal(self, status):
        return status in [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED
        ]