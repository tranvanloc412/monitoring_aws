from .base_plugin import BaseResourcePlugin
from .resource import Resource
from typing import List, Optional


class CWPlugin(BaseResourcePlugin):
    def __init__(self, session):
        self.client = session.client("cloudwatch")

    def filter_alarm_info(self, alarm: dict) -> Resource:
        """Extract relevant information from a CloudWatch alarm."""
        return Resource(
            type="CloudWatch Alarm",
            name=alarm.get("AlarmName", ""),
            id=alarm.get("AlarmArn", ""),
        )

    def discover_managed_resources(
        self, filter: Optional[str] = None
    ) -> List[Resource]:
        """Discover CloudWatch alarms managed by CMS."""
        try:
            response = self.client.describe_alarms(AlarmNamePrefix=f"{filter}-")

            resources = []
            for alarm in response.get("MetricAlarms", []):
                resources.append(self.filter_alarm_info(alarm))
            return resources

        except self.client.exceptions.ClientError as e:
            print(f"Error discovering CloudWatch alarms: {e}")
            return []
