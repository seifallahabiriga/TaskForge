class AuthException(Exception):
    """Base authentication exception."""


class UserAlreadyExistsError(AuthException):
    """Raised when attempting to register an existing user."""


class InvalidCredentialsError(AuthException):
    """Raised when credentials are invalid."""


class InvalidTokenError(AuthException):
    """Raised when token validation fails."""


class TaskException(Exception):
    """Base task exception"""


class TaskNotFoundError(TaskException):
    pass


class TaskPermissionError(TaskException):
    pass


class TaskExecutionError(TaskException):
    pass

class ExecutionNotFoundError(Exception):
    pass

class ResultNotFoundError(Exception):
    pass

class ModelNotFoundError(Exception):
    pass
 
class ModelInferenceError(Exception):
    pass

class AllProvidersFailedError(Exception):
    """Raised by the router when every provider in the chain has failed."""
    def __init__(self, errors: list):
        self.errors = errors
        summary = "; ".join(str(e) for e in errors)
        super().__init__(f"All providers failed: {summary}")

class ModelNotFoundError(Exception):
    """Raised when a ModelVersion row doesn't exist or no default is configured."""

class ModelInferenceError(Exception):
    """Raised when inference fails across all providers."""