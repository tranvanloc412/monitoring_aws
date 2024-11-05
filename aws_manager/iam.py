import boto3
import logging
from botocore.exceptions import ClientError, BotoCoreError
from dataclasses import dataclass
from typing import Optional
from .landing_zone import LandingZone

logger = logging.getLogger(__name__)


@dataclass
class AWSSession:
    session: boto3.Session
    aws_access_key: str
    aws_secret_key: str
    security_token: str
    expire_date: str


def assume_role(
    lz: LandingZone, role: str, region: str, role_session_name: str
) -> Optional[AWSSession]:
    """
    Assumes a specified role in an AWS account associated with the given landing zone (lz).
    """
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


def is_assume_role_session_valid() -> bool:
    """
    Checks if the current assumed role session is valid.
    """
    try:
        boto3.client("sts").get_caller_identity()
        logger.info("Assume role session is valid.")
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ["ExpiredToken", "InvalidClientTokenId"]:
            logger.error(
                "Assume role session is no longer valid due to expired or invalid token."
            )
        else:
            logger.error(f"Unexpected ClientError: {e}")
    except Exception as e:
        logger.error(
            f"Unexpected error while checking assume role session validity: {e}"
        )

    return False


def get_current_assumed_role() -> Optional[str]:
    """
    Retrieves the name of the currently assumed role, if any.
    """
    try:
        sts_client = boto3.client("sts")
        response = sts_client.get_caller_identity()
        arn = response["Arn"]

        if ":assumed-role/" in arn:
            role_name = arn.split(":assumed-role/")[1].split("/")[0]
            return role_name
        else:
            logger.warning("No assumed role found in the current session.")
            return None
    except ClientError as e:
        if e.response["Error"]["Code"] in ["ExpiredToken", "InvalidClientTokenId"]:
            logger.error("Assume role session is no longer valid.")
        else:
            logger.error(f"Unexpected ClientError: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while retrieving the assumed role: {e}")

    return None
