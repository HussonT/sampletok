"""
Custom exceptions for audio processing services.

Provides structured error handling for external API errors,
particularly for La La AI stem separation service.
"""


class LalalAIException(Exception):
    """Base exception for La La AI API errors"""

    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(self.message)


class LalalAPIKeyError(LalalAIException):
    """API key is invalid or missing"""

    def __init__(self, message: str = "Invalid or missing La La AI API key"):
        super().__init__(message, status_code=401)


class LalalRateLimitError(LalalAIException):
    """Rate limit exceeded for La La AI API"""

    def __init__(self, message: str = "Rate limit exceeded for La La AI API", retry_after: int = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class LalalQuotaExceededError(LalalAIException):
    """API quota or credits exhausted"""

    def __init__(self, message: str = "La La AI API quota or credits exhausted"):
        super().__init__(message, status_code=402)


class LalalFileError(LalalAIException):
    """File-related error (invalid format, too large, etc.)"""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, status_code=status_code)


class LalalProcessingError(LalalAIException):
    """Error during stem separation processing"""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message, status_code=status_code)


class LalalTimeoutError(LalalAIException):
    """Request to La La AI timed out"""

    def __init__(self, message: str = "Request to La La AI timed out"):
        super().__init__(message, status_code=504)
