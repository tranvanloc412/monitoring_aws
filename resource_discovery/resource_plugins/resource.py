from dataclasses import dataclass, field
from typing import List


@dataclass
class Resource:
    type: str  # EC2, RDS, etc.
    name: str  # Name tag
    id: str = ""  # Resource ID (e.g., instance-id, db-instance-identifier)
    related_resources: List[str] = field(default_factory=list)
