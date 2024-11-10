import boto3
import logging
from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime, timezone
from .landing_zone import LandingZone

logger = logging.getLogger(__name__)

DEFAULT_REGION = "ap-southeast-1"


@dataclass
class AWSSession:
    session: boto3.Session
    aws_access_key: str
    aws_secret_key: str
    security_token: str
    expire_date: str
    default_region: str = DEFAULT_REGION

    def is_valid(self) -> bool:
        """Check if the current session is valid and not expired."""
        try:
            self.session.client("sts").get_caller_identity()
            return datetime.fromisoformat(self.expire_date) > datetime.now(timezone.utc)
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return False

    @property
    def expires_in_seconds(self) -> Optional[float]:
        """Get the number of seconds until the session expires."""
        try:
            expire_dt = datetime.fromisoformat(self.expire_date)
            now = datetime.now(timezone.utc)
            return (expire_dt - now).total_seconds() if expire_dt > now else None
        except ValueError as e:
            logger.error(f"Invalid expiration date format: {e}")
            return None


def assume_role(
    lz: LandingZone, role: str, region: str, role_session_name: str
) -> Optional[AWSSession]:
    """Assumes a specified role in an AWS account."""
    role_arn = f"arn:aws:iam::{lz.account_id}:role/{role}"
    try:
        sts_creds = boto3.client("sts").assume_role(
            RoleArn=role_arn, RoleSessionName=f"{lz.name}-{role_session_name}"
        )["Credentials"]

        session = boto3.Session(
            aws_access_key_id=sts_creds["AccessKeyId"],
            aws_secret_access_key=sts_creds["SecretAccessKey"],
            aws_session_token=sts_creds["SessionToken"],
            region_name=region,
        )

        return AWSSession(
            session=session,
            aws_access_key=sts_creds["AccessKeyId"],
            aws_secret_key=sts_creds["SecretAccessKey"],
            security_token=sts_creds["SessionToken"],
            expire_date=sts_creds["Expiration"].isoformat(),
        )
    except Exception as e:
        logger.error(f"Failed to assume role {role_arn}: {e}")
        return None


class SessionManager:
    _sessions: Dict[str, AWSSession] = {}

    @classmethod
    def get_or_create_session(
        cls, lz: LandingZone, role: str, region: str, role_session_name: str
    ) -> AWSSession:
        session_key = f"{lz.account_id}:{role}"

        if session_key in cls._sessions and cls._sessions[session_key].is_valid():
            return cls._sessions[session_key]

        new_session = assume_role(lz, role, region, role_session_name)
        if new_session:
            cls._sessions[session_key] = new_session
        return new_session

    @classmethod
    def cleanup_session(cls, session: AWSSession) -> None:
        for session_key, stored_session in list(cls._sessions.items()):
            if stored_session is session:
                del cls._sessions[session_key]
                logger.info("Session successfully cleaned up")
                break
