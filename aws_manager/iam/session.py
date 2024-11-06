from dataclasses import dataclass
import boto3
import logging
from typing import Optional
from botocore.exceptions import ClientError, BotoCoreError
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class AWSSession:
    session: boto3.Session
    aws_access_key: str
    aws_secret_key: str
    security_token: str
    expire_date: str

    def is_valid(self) -> bool:
        """Check if the current session is valid and not expired."""
        try:
            # Verify session by calling STS get_caller_identity
            self.session.client("sts").get_caller_identity()
            expire_dt = datetime.fromisoformat(self.expire_date)
            if expire_dt <= datetime.now(timezone.utc):
                logger.warning("Session has expired")
                return False
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Session validation failed: {e}")
            return False
        except ValueError as e:
            logger.error(f"Invalid expiration date format: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during session validation: {e}")
            return False

    @property
    def expires_in_seconds(self) -> Optional[float]:
        """Get the number of seconds until the session expires."""
        try:
            expire_dt = datetime.fromisoformat(self.expire_date)
            now = datetime.now(timezone.utc)
            if expire_dt > now:
                return (expire_dt - now).total_seconds()
            logger.info("Session is already expired")
            return None
        except ValueError as e:
            logger.error(f"Invalid expiration date format: {e}")
            return None
