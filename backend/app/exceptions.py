"""
Custom exception types for payment and webhook processing.

These exceptions provide semantic meaning to error handling, making it clear
whether an error should trigger a retry or be treated as a permanent failure.

WEBHOOK RETRY STRATEGY:
- Stripe retries webhooks that receive 500-level responses
- Stripe does NOT retry webhooks that receive 200-level responses
- Therefore, we must distinguish between transient and permanent errors
"""


class BusinessLogicError(Exception):
    """
    Exception for permanent business logic errors that should NOT be retried.

    These errors indicate data validation issues, duplicate operations, or other
    problems that won't be resolved by retrying the same operation.

    When caught in webhook handlers, these should return HTTP 200 to prevent
    Stripe from retrying the webhook indefinitely.

    Examples:
    - Duplicate subscription for user (UNIQUE constraint violation)
    - User not found (data inconsistency - requires manual intervention)
    - Invalid Stripe data format (won't improve with retries)
    - Idempotency check indicates operation already completed

    Usage:
        if user_already_has_subscription:
            raise BusinessLogicError(f"User {user_id} already has active subscription")
    """

    def __init__(self, message: str, details: dict = None):
        """
        Args:
            message: Human-readable error description
            details: Optional dict of additional context for logging
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class TransientError(Exception):
    """
    Exception for temporary errors that MIGHT succeed on retry.

    These errors indicate infrastructure issues, rate limiting, or other
    transient problems that may be resolved by retrying later.

    When caught in webhook handlers, these should return HTTP 500 to trigger
    Stripe's retry mechanism (exponential backoff, multiple attempts).

    Examples:
    - Database connection timeout (might recover)
    - Database deadlock (retry may succeed)
    - Stripe API rate limit (will reset after delay)
    - Stripe API temporary unavailability
    - Network timeout to external service

    Usage:
        try:
            result = await db.execute(query)
        except OperationalError as e:
            raise TransientError(f"Database error: {e}") from e
    """

    def __init__(self, message: str, details: dict = None, original_exception: Exception = None):
        """
        Args:
            message: Human-readable error description
            details: Optional dict of additional context for logging
            original_exception: The underlying exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.original_exception = original_exception


class ConfigurationError(Exception):
    """
    Exception for missing or invalid configuration.

    These errors indicate that the application is misconfigured and cannot
    perform the requested operation. These should be caught during startup
    validation when possible, but may also occur at runtime for optional features.

    Examples:
    - Missing API key for optional integration
    - Invalid configuration value format
    - Required environment variable not set

    Usage:
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise ConfigurationError("STRIPE_WEBHOOK_SECRET not configured")
    """

    def __init__(self, message: str, config_key: str = None):
        """
        Args:
            message: Human-readable error description
            config_key: Name of the missing/invalid configuration key
        """
        super().__init__(message)
        self.message = message
        self.config_key = config_key
