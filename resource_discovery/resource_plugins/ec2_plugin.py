from .base_plugin import BaseResourcePlugin
from .resource import Resource
from typing import List, Optional


class EC2Plugin(BaseResourcePlugin):
    def __init__(self, session):
        self.client = session.client("ec2")

    def filter_instance_info(self, instance: dict) -> Resource:
        """Extract relevant information from an EC2 instance."""
        tags = instance.get("Tags", [])
        name = next((tag["Value"] for tag in tags if tag["Key"] == "Name"), "Unnamed")

        return Resource(
            type="EC2",
            name=name,
            id=instance.get("InstanceId", ""),
        )

    def discover_managed_resources(
        self, filter: Optional[str] = None
    ) -> List[Resource]:
        """Discover EC2 instances managed by CMS."""
        try:
            response = self.client.describe_instances(
                Filters=[{"Name": "tag:managed_by", "Values": ["CMS"]}]
            )

            resources = []
            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    resources.append(self.filter_instance_info(instance))
            return resources

        except self.client.exceptions.ClientError as e:
            print(f"Error discovering EC2 resources: {e}")
            return []
