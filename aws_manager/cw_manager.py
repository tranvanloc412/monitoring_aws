import yaml
from typing import Dict, Optional


class ConfigLoader:
    @staticmethod
    def load_yaml(file_path: str) -> Dict:
        with open(file_path, "r") as file:
            return yaml.safe_load(file)


class MetricConfig:
    def __init__(self, metric_file: str = "metrics_config.yml"):
        self.metrics = ConfigLoader.load_yaml(metric_file)

    def get_metric_settings(self, resource_type: str, metric_name: str) -> Optional[Dict[str, int]]:
        """
        Get the fixed metric settings for period and evaluation periods.
        """
        return self.metrics.get(resource_type, {}).get(metric_name)


class CategoryConfig:
    def __init__(self, category: str, category_file: str = "category_config.yml"):
        self.category = category
        self.configurations = ConfigLoader.load_yaml(category_file)

        if category not in self.configurations:
            raise ValueError(f"Unknown category '{category}'. Must be one of {', '.join(self.configurations.keys())}.")

    def get_threshold(self, resource_type: str, metric_name: str) -> Optional[int]:
        """
        Get the threshold for a specific resource type and metric based on the category.
        """
        return self.configurations.get(self.category, {}).get(resource_type, {}).get(metric_name)


# Usage example
metric_config = MetricConfig()
category_config = CategoryConfig("A")

# Get metric settings for EC2 CPUUtilization
ec2_cpu_settings = metric_config.get_metric_settings("EC2", "CPUUtilization")
print("EC2 CPU Metric Settings:", ec2_cpu_settings)

# Get threshold for EC2 CPUUtilization under category A
ec2_cpu_threshold = category_config.get_threshold("EC2", "CPUUtilization")
print("EC2 CPU Threshold (Category A):", ec2_cpu_threshold)