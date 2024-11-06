class AWSManagerError(Exception):
    """Base exception for aws_manager package."""

    pass


class ConfigurationError(AWSManagerError):
    """Raised when there's a configuration error."""

    pass


class ValidationError(AWSManagerError):
    """Raised when validation fails."""

    pass


class LandingZoneError(AWSManagerError):
    """Raised when Landing Zone operations fail."""

    pass


class SessionError(AWSManagerError):
    """Raised when session operations fail."""

    pass


class CloudWatchError(AWSManagerError):
    """Raised when CloudWatch operations fail."""

    pass


class ResourceError(AWSManagerError):
    """Raised when resource operations fail."""

    pass
