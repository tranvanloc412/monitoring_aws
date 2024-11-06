import boto3
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from botocore.exceptions import BotoCoreError, ClientError
from ..iam import AWSSession
from ..core import MANAGE_BY_TAG_KEY, CMS_MANAGED_TAG_VALUE

logger = logging.getLogger(__name__)


@dataclass
class Resource:
    resource_type: str
    resource_name: str
    resource_id: str


class ResourceScanner:
    ARN_PATTERNS = {
        "EC2": (":instance/", lambda arn: arn.split("/")[-1]),
        "RDS": (":db:", lambda arn: arn.split(":")[-1]),
        "CloudWatch": (":alarm:", lambda arn: arn.split(":")[-1]),
    }
    SUPPORT_RESOURCE_TYPES = {
        "EC2": "ec2:instance",
        "RDS": "rds:db",
    }

    def __init__(
        self, session: Optional[AWSSession] = None, region_name: Optional[str] = None
    ):
        self.client = (
            session.session.client(
                "resourcegroupstaggingapi",
                region_name=region_name or session.session.region_name,
            )
            if session
            else boto3.client("resourcegroupstaggingapi", region_name=region_name)
        )
        self._managed_resources: List[Resource] = []

    def get_managed_resources(
        self, tag_key: str = MANAGE_BY_TAG_KEY, tag_value: str = CMS_MANAGED_TAG_VALUE
    ) -> List[Resource]:
        if not self._managed_resources:
            self._managed_resources = self._get_resources_by_tag(tag_key, tag_value)
        return self._managed_resources

    def get_managed_resources_by_type(self, resource_type: str) -> List[Resource]:
        return [
            resource
            for resource in self._managed_resources
            if resource.resource_type == resource_type
        ]

    def _get_resources_by_tag(
        self,
        tag_key: str,
        tag_value: str,
        supported_resource_types: Optional[Dict[str, str]] = None,
    ) -> List[Resource]:
        all_resources = []

        # Filter resource types if specified, otherwise use all supported types
        resource_types = (
            supported_resource_types
            if supported_resource_types is not None
            else self.SUPPORT_RESOURCE_TYPES
        )

        for resource_type, resource_type_value in resource_types.items():
            try:
                response = self._fetch_resources_from_aws(
                    tag_key, tag_value, resource_type_value
                )
                for item in response:
                    resource = Resource(
                        resource_type=resource_type,
                        resource_name=self._extract_resource_name(item.get("Tags", [])),
                        resource_id=self._extract_resource_id(item["ResourceARN"]),
                    )
                    all_resources.append(resource)
            except (BotoCoreError, ClientError) as e:
                logger.error(
                    f"Failed to retrieve resources for type {resource_type} with tag {tag_key}: {e}"
                )

        return all_resources

    def _fetch_resources_from_aws(
        self, tag_key: str, tag_value: str, resource_type: str
    ) -> List[Dict]:
        try:
            response = self.client.get_resources(
                TagFilters=[{"Key": tag_key, "Values": [tag_value]}],
                ResourceTypeFilters=[resource_type],
            )
            return response.get("ResourceTagMappingList", [])
        except (BotoCoreError, ClientError) as e:
            logger.error(
                f"Failed to fetch resources from AWS for type {resource_type} with tag {tag_key}: {e}"
            )
            return []

    def _extract_resource_id(self, arn: str) -> str:
        for _, (pattern, extractor) in self.ARN_PATTERNS.items():
            if pattern in arn:
                return extractor(arn)
        logger.warning(f"ARN pattern not found for ARN: {arn}")
        return ""

    def _extract_resource_name(self, tags: List[Dict[str, str]]) -> str:
        for tag in tags:
            if tag.get("Key") == "Name":
                return tag.get("Value", "Unnamed")
        return "Unnamed"
