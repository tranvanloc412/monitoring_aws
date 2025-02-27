from botocore.exceptions import ClientError
import logging
from typing import List, Optional
import boto3

from .base_plugin import BaseResourcePlugin
from .resource import Resource

logger = logging.getLogger(__name__)


class ALBPlugin(BaseResourcePlugin):
    """Plugin for discovering Application Load Balancer resources."""

    def __init__(self, region: str):
        """Initialize ALB client witsh boto3 session."""
        self.region = region
        self.elbv2_client = boto3.client("elbv2", region_name=region)

    def _get_tag_value(
        self, tags: List[dict], key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Helper method to extract tag value."""
        return next((tag["Value"] for tag in tags if tag["Key"] == key), default)

    def discover(self) -> List[Resource]:
        resources = []

        # Get all load balancers
        load_balancers = self.elbv2_client.describe_load_balancers()["LoadBalancers"]

        for lb in load_balancers:
            # Get target groups for this load balancer
            target_groups = self.elbv2_client.describe_target_groups(
                LoadBalancerArn=lb["LoadBalancerArn"]
            )["TargetGroups"]

            # Create a resource for each target group
            for tg in target_groups:
                # Extract the load balancer name from ARN
                lb_name = lb["LoadBalancerName"]

                # Create dimensions with both LoadBalancer and TargetGroup
                dimensions = [
                    {"Name": "LoadBalancer", "Value": lb_name},
                    {"Name": "TargetGroup", "Value": tg["TargetGroupName"]},
                ]

                resource = Resource(
                    type="ALB",
                    name=f"{lb_name}-{tg['TargetGroupName']}",
                    id=lb_name,  # Using LB name as the primary ID
                    dimensions=dimensions,
                    region=self.region,
                )
                resources.append(resource)

        return resources

    def discover_managed_resources(
        self, filter: Optional[str] = None
    ) -> List[Resource]:
        """
        Discover ALBs managed by CMS and attach target group information as dimensions.

        Args:
            filter: Optional filter string to filter resources (e.g., by name or tag)

        Returns:
            List[Resource]: A list of ALB resources with additional CW dimensions
            populated from all target groups attached to the ALB.
        """
        try:
            # Describe ALBs
            response = self.elbv2_client.describe_load_balancers()
            alb_list = [
                alb
                for alb in response.get("LoadBalancers", [])
                if alb["Type"] == "application"
            ]
            alb_arns = [alb["LoadBalancerArn"] for alb in alb_list]

            # Describe tags for all ALBs
            tag_response = self.elbv2_client.describe_tags(ResourceArns=alb_arns)
            alb_tags = {
                desc["ResourceArn"]: desc.get("Tags", [])
                for desc in tag_response.get("TagDescriptions", [])
            }

            # Describe all target groups (note: this call returns all target groups)
            tg_response = self.elbv2_client.describe_target_groups()
            # Build a mapping from ALB ARN to list of target groups
            alb_to_tg = {}
            for tg in tg_response.get("TargetGroups", []):
                # Some target groups may not be associated with a specific ALB.
                lb_arn = tg.get("LoadBalancerArn")
                if lb_arn:
                    alb_to_tg.setdefault(lb_arn, []).append(tg)

            resources = []
            # Process each ALB
            for alb in alb_list:
                tags = alb_tags.get(alb["LoadBalancerArn"], [])
                # Only include ALBs managed by CMS.
                if self._get_tag_value(tags, "managed_by") == "CMS":
                    # Apply filter if provided
                    if filter and filter not in alb["LoadBalancerName"]:
                        continue

                    # Prepare CW dimensions.
                    cw_dimensions = []
                    # Add dimensions for all target groups
                    target_groups = alb_to_tg.get(alb["LoadBalancerArn"], [])
                    for tg in target_groups:
                        cw_dimensions.append(
                            {
                                "Name": "TargetGroup",
                                "Value": tg["TargetGroupName"],
                            }  # Use name instead of ARN
                        )

                    if not target_groups:
                        cw_dimensions.append(
                            {"Name": "TargetGroup", "Value": "unknown"}
                        )

                    # Add LoadBalancer dimension using name instead of ARN for consistency
                    cw_dimensions.append(
                        {"Name": "LoadBalancer", "Value": alb["LoadBalancerName"]}
                    )

                    # Add AvailabilityZone dimensions for all AZs
                    if alb.get("AvailabilityZones"):
                        for az_info in alb["AvailabilityZones"]:
                            cw_dimensions.append(
                                {
                                    "Name": "AvailabilityZone",
                                    "Value": az_info.get("ZoneName", "unknown"),
                                }
                            )
                    else:
                        cw_dimensions.append(
                            {"Name": "AvailabilityZone", "Value": "unknown"}
                        )

                    # Build the Resource instance with region
                    resource = Resource(
                        type="ALB",
                        name=self._get_tag_value(tags, "Name", alb["LoadBalancerName"]),
                        id=alb["LoadBalancerArn"],
                        dimensions=cw_dimensions,
                        region=self.region,  # Add region
                    )
                    resources.append(resource)
            return resources

        except ClientError as e:
            logger.error(f"Error discovering ALB resources: {e}")
            return []
