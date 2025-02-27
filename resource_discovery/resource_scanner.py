import importlib
import os
import sys
from typing import List, Dict, Any
from .resource_plugins.resource import Resource


supported_services = ["ec2", "rds", "cw"]


class ResourceScanner:
    def __init__(self, session) -> None:
        self._session = session
        self.plugins = self._load_plugins()

    def _load_plugins(self) -> Dict[str, Any]:
        plugins = {}

        # Ensure the plugins directory is in the Python path
        sys.path.append(os.path.dirname(__file__))

        for service in supported_services:
            try:
                module = importlib.import_module(f"resource_plugins.{service}_plugin")
                plugin_class = getattr(module, f"{service.upper()}Plugin")
                plugins[service] = plugin_class(self._session)
            except ImportError as e:
                print(f"Failed to load plugin for {service}: {str(e)}")
            except AttributeError as e:
                print(f"Plugin class not found for {service}: {str(e)}")

        return plugins

    def scan_all_supported_resources(self, lz_name: str) -> List[Resource]:
        discovered_resources: List[Resource] = []

        for service_name, plugin in self.plugins.items():
            try:
                resources = plugin.discover_managed_resources()
                discovered_resources.extend(resources)
            except Exception as e:
                print(f"Error scanning resources for {service_name}: {str(e)}")

        return discovered_resources

    def scan_resources(
        self,
        service_name: str,
        lz_name: str,
    ) -> List[Resource]:
        if service_name not in self.plugins:
            raise ValueError(f"Unsupported service: {service_name}")

        plugin = self.plugins[service_name]
        return plugin.discover_managed_resources(lz_name)
