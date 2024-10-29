import boto3
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class Resource:
    resource_type: str
    resource_name: str
    resource_id: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


class ResourceScanner:
    def __init__(self, region_name: str = "ap-southeast-1"):
        self.client = boto3.client("resourcegroupstaggingapi", region_name=region_name)

    def get_managed_resources(
        self, tag_key: str = "managed_by", tag_value: str = "CMS"
    ) -> List[Resource]:
        """
        Scan AWS resources with a specific tag key-value pair.
        """
        resources = []
        paginator = self.client.get_paginator("get_resources")

        for page in paginator.paginate(
            TagFilters=[{"Key": tag_key, "Values": [tag_value]}]
        ):
            for resource_tag_mapping in page["ResourceTagMappingList"]:
                arn = resource_tag_mapping["ResourceARN"]

                # Extract resource type and ID based on ARN pattern
                resource_type, resource_id = self._extract_resource_type_and_id(arn)
                if resource_type is None or resource_id is None:
                    continue  # Skip unsupported resource types

                # Extract resource name from tags
                resource_name = self._extract_resource_name(
                    resource_tag_mapping["Tags"]
                )

                # Create and append a Resource object
                resource = Resource(
                    resource_type=resource_type,
                    resource_name=resource_name,
                    resource_id=resource_id,
                )
                resources.append(resource)

        return resources

    def _extract_resource_type_and_id(
        self, arn: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract the resource type and ID from an ARN.
        """
        arn_patterns = {
            "EC2": (":instance/", lambda arn: arn.split("/")[-1]),
            "RDS": (":db:", lambda arn: arn.split(":")[-1]),
            # Add other resource patterns here as needed
        }

        for resource_type, (pattern, extractor) in arn_patterns.items():
            if pattern in arn:
                return resource_type, extractor(arn)

        # If the ARN doesn't match any known patterns, return None
        return None, None

    def _extract_resource_name(self, tags: List[Dict[str, str]]) -> str:
        """
        Extract the 'Name' tag from a list of tags, or return 'Unnamed' if not found.
        """
        for tag in tags:
            if tag["Key"] == "Name":
                return tag["Value"]
        return "Unnamed"
