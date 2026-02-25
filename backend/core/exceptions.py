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