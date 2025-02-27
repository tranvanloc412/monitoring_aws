from abc import ABC, abstractmethod
from typing import List, Optional


from .resource import Resource


class BaseResourcePlugin(ABC):
    @abstractmethod
    def discover_managed_resources(
        self, filter: Optional[str] = None
    ) -> List[Resource]:
        """
        Discover and return a list of CMS managed resources.
        """
        pass
