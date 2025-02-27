from .base_plugin import BaseResourcePlugin, Resource
from typing import List, Optional
from .resource import Resource
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class RDSPlugin(BaseResourcePlugin):
    """Plugin for discovering RDS database instances."""

    def __init__(self, session):
        """Initialize RDS client with boto3 session."""
        self.client = session.client("rds")

    def _get_tag_value(
        self, tags: List[dict], key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Helper method to extract tag value."""
        return next((tag["Value"] for tag in tags if tag["Key"] == key), default)

    def filter_instance_info(self, instance: dict) -> Resource:
        """Extract relevant information from an RDS instance."""
        tags = instance.get("TagList", [])
        name = self._get_tag_value(tags, "Name", instance["DBInstanceIdentifier"])

        return Resource(
            type="RDS",
            name=name or "unnamed-rds-instance",
            id=instance["DBInstanceIdentifier"],
            platform=instance.get("PlatformDetails", ""),
        )

    def discover_managed_resources(
        self, filter: Optional[str] = None
    ) -> List[Resource]:
        """Discover RDS instances managed by CMS."""
        try:
            response = self.client.describe_db_instances()
            resources = []

            for instance in response.get("DBInstances", []):
                tags = instance.get("TagList", [])
                if self._get_tag_value(tags, "managed_by") == "CMS":
                    resources.append(self.filter_instance_info(instance))

            return resources

        except ClientError as e:
            print(f"Error discovering RDS resources: {e}")
            return []
