import enum

# -------------------------
# User
# -------------------------

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    USER = "USER"


# -------------------------
# Task
# -------------------------

class TaskType(str, enum.Enum):
    INFERENCE = "INFERENCE"
    TRAINING = "TRAINING"
    ANALYSIS = "ANALYSIS"


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


# -------------------------
# Execution
# -------------------------

class ExecutionStatus(str, enum.Enum):
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


# -------------------------
# Worker
# -------------------------

class WorkerStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    BUSY = "BUSY"


class WorkerType(str, enum.Enum):
    CPU = "CPU"
    GPU = "GPU"
    GPU_HIGH_MEM = "GPU_HIGH_MEM"