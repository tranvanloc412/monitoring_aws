import boto3
import logging
from botocore.exceptions import ClientError, BotoCoreError
from typing import Optional, Dict
from datetime import datetime, timezone
from .session import AWSSession
from aws_manager.landing_zone import LandingZone

logger = logging.getLogger(__name__)


def assume_role(
    lz: LandingZone, role: str, region: str, role_session_name: str
) -> Optional[AWSSession]:
    """Assumes a specified role in an AWS account."""

    role_session_name = f"{lz.name}-{role_session_name}"
    role_arn = f"arn:aws:iam::{lz.account_id}:role/{role}"
    try:
        sts_client = boto3.client("sts")
        sts_creds = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=role_session_name
        )["Credentials"]

        aws_access_key = sts_creds["AccessKeyId"]
        aws_secret_key = sts_creds["SecretAccessKey"]
        security_token = sts_creds["SessionToken"]
        expire_date = sts_creds["Expiration"].isoformat()

        session = boto3.Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            aws_session_token=security_token,
        )

        logger.info(f"Successfully assumed role: {role_arn} - {lz.name}")
        return AWSSession(
            session, aws_access_key, aws_secret_key, security_token, expire_date
        )
    except ClientError as e:
        logger.error(
            f"Failed to assume role {role_arn}: with session name {role_session_name}: {e}"
        )
    except BotoCoreError as e:
        logger.error(f"BotoCoreError occurred while assuming role {role_arn}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when assuming role {role_arn}: {e}")

    return None


class SessionManager:
    _sessions: Dict[str, AWSSession] = {}

    @classmethod
    def get_or_create_session(
        cls, lz: LandingZone, role: str, region: str, role_session_name: str
    ) -> Optional[AWSSession]:
        session_key = f"{lz.account_id}:{role}"

        if session_key in cls._sessions:
            session = cls._sessions[session_key]
            if not cls._is_session_expired(session):
                return session

        new_session = assume_role(lz, role, region, role_session_name)
        if new_session:
            cls._sessions[session_key] = new_session
        return new_session

    @staticmethod
    def _is_session_expired(session: AWSSession) -> bool:
        expire_date = datetime.fromisoformat(session.expire_date)
        return expire_date <= datetime.now(timezone.utc)

    @classmethod
    def cleanup_session(cls, session: AWSSession) -> None:
        try:
            # Find and remove the session from _sessions dictionary
            for session_key, stored_session in cls._sessions.items():
                if stored_session is session:
                    del cls._sessions[session_key]
                    logger.info("Session successfully cleaned up")
                    break
        except Exception as e:
            logger.error(f"Error cleaning up session: {e}")
