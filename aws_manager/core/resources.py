import boto3
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from botocore.exceptions import BotoCoreError, ClientError
from .session import AWSSession

logger = logging.getLogger(__name__)


@dataclass
class Resource:
    type: str
    name: str
    id: str
    # os_type: Optional[str] = None


class ResourceScanner:
    RESOURCE_CONFIG = {
        "EC2": {"type": "ec2:instance", "delimiter": "/"},
        "RDS": {"type": "rds:db", "delimiter": ":"},
    }

    # def _detect_os_type(self, resource_name: str) -> Optional[str]:
    #     # Check for pattern: xxxLxxx1234 or xxxWxxx1234
    #     if len(resource_name) >= 8 and resource_name[-4:].isdigit():
    #         # Extract the OS identifier letter (4 positions before the digits)
    #         os_identifier = resource_name[-8].upper()
    #         if os_identifier == "W":
    #             return "Windows"
    #         elif os_identifier == "L":
    #             return "Linux"
    #     # Return None if pattern doesn't match
    #     return None

    def __init__(self, session: AWSSession, region_name: Optional[str] = None):
        self.client = session.session.client(
            "resourcegroupstaggingapi",
            region_name=region_name or getattr(session, "region_name", None),
        )
        self._managed_resources: List[Resource] = []

    def get_managed_resources(self, env: str) -> List[Resource]:
        tags = {"managed_by": "CMS"}
        if env == "prod":
            tags["Environment"] = env

        if not self._managed_resources:
            self._managed_resources = self.get_resources_by_tag(
                tags, self.RESOURCE_CONFIG
            )
        return self._managed_resources

    def get_resources_by_tag(
        self, tags: Dict[str, str], resource_config: Dict[str, Dict[str, str]]
    ) -> List[Resource]:
        if not tags:
            raise ValueError("At least one tag must be provided")

        all_resources = []
        for resource_type, config in resource_config.items():
            resources = self._fetch_resources_from_aws(tags, config["type"])
            for item in resources:
                resource_name = next(
                    (
                        tag["Value"]
                        for tag in item.get("Tags", [])
                        if tag["Key"] == "Name"
                    ),
                    "Unnamed",
                )
                resource = Resource(
                    type=resource_type,
                    name=resource_name,
                    id=item["ResourceARN"].split(config["delimiter"])[-1],
                    # os_type=(
                    #     self._detect_os_type(resource_name)
                    #     if resource_type == "EC2"
                    #     else None
                    # ),
                )
                all_resources.append(resource)
        return all_resources

    def _fetch_resources_from_aws(
        self, tags: Dict[str, str], resource_type: str
    ) -> List[Dict]:
        try:
            response = self.client.get_resources(
                TagFilters=[{"Key": k, "Values": [v]} for k, v in tags.items()],
                ResourceTypeFilters=[resource_type],
            )
            return response.get("ResourceTagMappingList", [])
        except (BotoCoreError, ClientError) as e:
            logger.error(f"AWS resource fetch failed: {e}")
            return []
