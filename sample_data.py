# landing_zones
[LandingZone(name="cmsnonprod", account_id=891377130283, category="CAT_A")]


# thresholds
{
    "EC2_CAT_A": {
        "CPUUtilization": 70,
        "MemoryUtilization": 75,
        "DiskSpaceUtilization": 80,
    },
    "RDS_CAT_A": {"CPUUtilization": 65, "FreeStorageSpace": 20},
    "EC2_CAT_B": {
        "CPUUtilization": 70,
        "MemoryUtilization": 75,
        "DiskSpaceUtilization": 80,
    },
    "RDS_CAT_B": {"CPUUtilization": 65, "FreeStorageSpace": 20},
}


# metrics
{
    "EC2": {
        "CPUUtilization": MetricSettings(
            resource_type="EC2",
            name="CPUUtilization",
            namespace="AWS/EC2",
            statistic="average",
            comparison="GreaterThanThreshold",
            unit="Percent",
            period=300,
            evaluation_periods=3,
        ),
        "MemoryUtilization": MetricSettings(
            resource_type="EC2",
            name="MemoryUtilization",
            namespace="AWS/EC2",
            statistic="average",
            comparison="GreaterThanThreshold",
            unit="Percent",
            period=300,
            evaluation_periods=2,
        ),
        "DiskSpaceUtilization": MetricSettings(
            resource_type="EC2",
            name="DiskSpaceUtilization",
            namespace="AWS/EC2",
            statistic="average",
            comparison="GreaterThanThreshold",
            unit="Percent",
            period=300,
            evaluation_periods=2,
        ),
    },
    "RDS": {
        "CPUUtilization": MetricSettings(
            resource_type="RDS",
            name="CPUUtilization",
            namespace="AWS/RDS",
            statistic="average",
            comparison="GreaterThanThreshold",
            unit="Percent",
            period=300,
            evaluation_periods=3,
        ),
        "FreeStorageSpace": MetricSettings(
            resource_type="RDS",
            name="FreeStorageSpace",
            namespace="AWS/RDS",
            statistic="average",
            comparison="GreaterThanThreshold",
            unit="Percent",
            period=3600,
            evaluation_periods=1,
        ),
    },
}


# Resources
Resources(
    resources_by_type={
        "EC2": [
            Resource(
                resource_type="EC2",
                resource_name="CMSLIDA9001",
                resource_id="i-0edbded74c49e63a1",
            ),
            Resource(
                resource_type="EC2",
                resource_name="CMSLIDA9002",
                resource_id="i-037803613b65e0e7c",
            ),
        ],
        "RDS": [
            Resource(
                resource_type="RDS",
                resource_name="database-1",
                resource_id="database-1",
            )
        ],
    }
)


#  all_alarm_definition:
[
    AlarmConfig(
        metric_settings=MetricSettings(
            resource_type="EC2",
            name="CPUUtilization",
            namespace="AWS/EC2",
            statistic="average",
            comparison="GreaterThanThreshold",
            unit="Percent",
            period=300,
            evaluation_periods=3,
        ),
        threshold_value=70,
        sns_topic_arns=["arn:aws:sns:ap-southeast-1:891377130283:HIPNotifyTopicLow"],
    ),
    AlarmConfig(
        metric_settings=MetricSettings(
            resource_type="EC2",
            name="MemoryUtilization",
            namespace="AWS/EC2",
            statistic="average",
            comparison="GreaterThanThreshold",
            unit="Percent",
            period=300,
            evaluation_periods=2,
        ),
        threshold_value=75,
        sns_topic_arns=["arn:aws:sns:ap-southeast-1:891377130283:HIPNotifyTopicLow"],
    ),
    AlarmConfig(
        metric_settings=MetricSettings(
            resource_type="EC2",
            name="DiskSpaceUtilization",
            namespace="AWS/EC2",
            statistic="average",
            comparison="GreaterThanThreshold",
            unit="Percent",
            period=300,
            evaluation_periods=2,
        ),
        threshold_value=80,
        sns_topic_arns=["arn:aws:sns:ap-southeast-1:891377130283:HIPNotifyTopicLow"],
    ),
    AlarmConfig(
        metric_settings=MetricSettings(
            resource_type="EC2",
            name="CPUUtilization",
            namespace="AWS/EC2",
            statistic="average",
            comparison="GreaterThanThreshold",
            unit="Percent",
            period=300,
            evaluation_periods=3,
        ),
        threshold_value=70,
        sns_topic_arns=["arn:aws:sns:ap-southeast-1:891377130283:HIPNotifyTopicLow"],
    ),
    AlarmConfig(
        metric_settings=MetricSettings(
            resource_type="EC2",
            name="MemoryUtilization",
            namespace="AWS/EC2",
            statistic="average",
            comparison="GreaterThanThreshold",
            unit="Percent",
            period=300,
            evaluation_periods=2,
        ),
        threshold_value=75,
        sns_topic_arns=["arn:aws:sns:ap-southeast-1:891377130283:HIPNotifyTopicLow"],
    ),
    AlarmConfig(
        metric_settings=MetricSettings(
            resource_type="EC2",
            name="DiskSpaceUtilization",
            namespace="AWS/EC2",
            statistic="average",
            comparison="GreaterThanThreshold",
            unit="Percent",
            period=300,
            evaluation_periods=2,
        ),
        threshold_value=80,
        sns_topic_arns=["arn:aws:sns:ap-southeast-1:891377130283:HIPNotifyTopicLow"],
    ),
    AlarmConfig(
        metric_settings=MetricSettings(
            resource_type="RDS",
            name="CPUUtilization",
            namespace="AWS/RDS",
            statistic="average",
            comparison="GreaterThanThreshold",
            unit="Percent",
            period=300,
            evaluation_periods=3,
        ),
        threshold_value=65,
        sns_topic_arns=["arn:aws:sns:ap-southeast-1:891377130283:HIPNotifyTopicLow"],
    ),
    AlarmConfig(
        metric_settings=MetricSettings(
            resource_type="RDS",
            name="FreeStorageSpace",
            namespace="AWS/RDS",
            statistic="average",
            comparison="GreaterThanThreshold",
            unit="Percent",
            period=3600,
            evaluation_periods=1,
        ),
        threshold_value=20,
        sns_topic_arns=["arn:aws:sns:ap-southeast-1:891377130283:HIPNotifyTopicLow"],
    ),
]
