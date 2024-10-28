import os
import subprocess
import logging
from typing import Dict, Optional, Protocol

# Define the session protocol
class SessionProtocol(Protocol):
    aws_access_key: str
    aws_secret_key: str
    security_token: str

# Setup logging
logger = logging.getLogger(__name__)

def set_aws_env_vars(session: SessionProtocol) -> Dict[str, str]:
    """
    Prepare AWS environment variables from the provided session details.
    """
    env_vars = os.environ.copy()
    env_vars.update({
        "AWS_ACCESS_KEY_ID": session.aws_access_key,
        "AWS_SECRET_ACCESS_KEY": session.aws_secret_key,
        "AWS_SESSION_TOKEN": session.security_token,
        "AWS_DEFAULT_REGION": os.getenv("AWS_DEFAULT_REGION", "ap-southeast-1")
    })
    return env_vars

def build_ansible_command(
    playbook_path: str,
    inventory_path: str,
    extra_vars: Optional[Dict[str, str]] = None
) -> list:
    command = ["ansible-playbook", "-i", inventory_path, playbook_path]
    if extra_vars:
        extra_vars_string = " ".join(f"{key}={value}" for key, value in extra_vars.items())
        command.extend(["--extra-vars", extra_vars_string])
    return command

def run_ansible_playbook(
    playbook_path: str,
    inventory_path: str,
    extra_vars: Optional[Dict[str, str]] = None,
    session: Optional[SessionProtocol] = None
) -> None:
    if session is None:
        logger.error("AWS session details are required but were not provided.")
        raise ValueError("AWS session details are required to run the playbook")
    
    env_vars = set_aws_env_vars(session)
    command = build_ansible_command(playbook_path, inventory_path, extra_vars)
    logger.info(f"Executing Ansible playbook: {playbook_path} with inventory {inventory_path}")
    
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, env=env_vars
        )
        logger.info("Ansible playbook executed successfully.")
        logger.debug(f"Output:\n{result.stdout}")

    except subprocess.CalledProcessError as e:
        logger.error("Failed to run Ansible playbook.")
        logger.error(f"Command: {' '.join(command)}")
        logger.error(f"Error Message: {e.stderr.strip()}")
        logger.error(f"Return Code: {e.returncode}")
        raise RuntimeError(f"Failed to execute playbook {playbook_path}")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        raise