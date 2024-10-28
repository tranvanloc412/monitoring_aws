import boto3
import logging

from botocore.exceptions import ClientError, BotoCoreError
from typing import Optional
from dataclasses import dataclass

from .landing_zone_manager import LandingZone


logger = logging.getLogger(__name__)


@dataclass
class AWSSessionDetails:
    session: boto3.Session
    aws_access_key: str
    aws_secret_key: str
    security_token: str
    expire_date: str


def assume_role(
    lz: LandingZone, role: str, role_session_name: Optional[str] = None
) -> Optional[AWSSessionDetails]:
    """
    Assumes a specified role in an AWS account associated with the given landing zone (lz).

    :param lz: LandingZone instance containing AWS account details.
    :param role: Name of the IAM role to assume.
    :param role_session_name: Optional session name; defaults to "<landing_zone_name>-CMSMonitoring".
    :return: AWSSessionDetails if successful, None otherwise.
    """
    if not role_session_name:
        role_session_name = f"{lz.name}-CMSMonotoring"

    role_arn = f"arn:aws:iam::{lz.account_id}:role/{role}"
    try:
        sts_client = boto3.client("sts")
        sts_creds = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=role_session_name
        )

        aws_access_key = sts_creds["Credentials"]["AccessKeyId"]
        aws_secret_key = sts_creds["Credentials"]["SecretAccessKey"]
        security_token = sts_creds["Credentials"]["SessionToken"]
        expire_date = sts_creds["Credentials"]["Expiration"].isoformat()

        session = boto3.Session(
            region_name=lz.region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            aws_session_token=security_token,
        )

        logger.info(f"Successfully assumed role: {role_arn} - {lz.name}")
        return AWSSessionDetails(
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

    :return: True if session is valid, False otherwise.
    """
    try:
        sts_client = boto3.client("sts")
        sts_client.get_caller_identity()
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

    :return: Role name as a string if found, None otherwise.
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
