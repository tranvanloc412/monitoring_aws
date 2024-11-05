import boto3
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from botocore.exceptions import BotoCoreError, ClientError
from .iam import AWSSession

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
    }
    SUPPORT_RESOURCE_TYPES = {
        "EC2": "ec2:instance",
        "RDS": "rds:db",
    }

    MANAGE_BY_TAG_KEY = "managed_by"
    CMS_MANAGED_TAG_VALUE = "CMS"

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
        if self._managed_resources:
            return self._managed_resources
        return self._get_resources_by_tag(tag_key, tag_value)

    def get_managed_resources_by_type(self, resource_type: str) -> List[Resource]:
        return [
            resource
            for resource in self._managed_resources
            if resource.resource_type == resource_type
        ]

    def _get_resources_by_tag(self, tag_key: str, tag_value: str) -> List[Resource]:
        all_resources = []

        for resource_type, resource_type_value in self.SUPPORT_RESOURCE_TYPES.items():
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
                logger.error(f"Failed to retrieve resources by tag: {e}")

        self._managed_resources = all_resources
        return self._managed_resources

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
            logger.error(f"Failed to fetch resources from AWS: {e}")
            return []

    def _extract_resource_id(self, arn: str) -> str:
        for _, (pattern, extractor) in self.ARN_PATTERNS.items():
            if pattern in arn:
                return extractor(arn)
        return ""

    def _extract_resource_name(self, tags: List[Dict[str, str]]) -> str:
        for tag in tags:
            if tag.get("Key") == "Name":
                return tag.get("Value", "Unnamed")
        return "Unnamed"


# @dataclass
# class Resources:
#     resources_by_type: Dict[str, List[Resource]] = field(default_factory=dict)

#     def add_resource(self, resource: Resource) -> None:
#         """Adds a resource to the appropriate type group within resources_by_type."""
#         if resource.resource_type not in self.resources_by_type:
#             self.resources_by_type[resource.resource_type] = []
#         self.resources_by_type[resource.resource_type].append(resource)

#     def get_resources(self, resource_type: str) -> List[Resource]:
#         """Retrieve all resources of a specific type."""
#         return self.resources_by_type.get(resource_type, [])

#     def all_resources(self) -> List[Resource]:
#         """Returns a flat list of all resources."""
#         return [
#             res for resources in self.resources_by_type.values() for res in resources
#         ]
