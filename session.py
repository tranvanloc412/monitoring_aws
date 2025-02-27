import boto3
import logging
from typing import Dict

logger = logging.getLogger(__name__)

DEFAULT_REGION = "ap-southeast-1"


def assume_role(
    account_id: str,
    account_name: str,
    role: str,
    region: str = DEFAULT_REGION,
    role_session_name: str = "default",
) -> boto3.Session:
    """Assumes a specified role in an AWS account and returns a boto3 Session."""
    role_arn = f"arn:aws:iam::{account_id}:role/{role}"
    try:
        sts_client = boto3.client("sts")
        credentials = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=f"{account_name}-{role_session_name}"
        )["Credentials"]

        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=region,
        )
    except Exception as e:
        logger.error(f"Failed to assume role {role_arn}: {e}")
        raise


class SessionManager:
    _sessions: Dict[str, boto3.Session] = {}

    @classmethod
    def get_session(
        cls,
        account_id: str,
        account_name: str,
        role: str,
        region: str = DEFAULT_REGION,
        role_session_name: str = "default",
    ) -> boto3.Session:
        """Get or create a boto3 Session for the specified AWS role."""
        session_key = f"{account_id}:{role}"

        if session_key not in cls._sessions:
            cls._sessions[session_key] = assume_role(
                account_id, account_name, role, region, role_session_name
            )

        return cls._sessions[session_key]

    @classmethod
    def clear_session(cls, account_id: str, role: str) -> None:
        """Remove a session from the cache."""
        session_key = f"{account_id}:{role}"
        if session_key in cls._sessions:
            del cls._sessions[session_key]
            logger.info(f"Session cleared for {session_key}")
