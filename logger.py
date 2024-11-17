import logging
from pathlib import Path
from typing import Dict


class LoggerSetup:
    def __init__(self, log_format: str):
        self.log_format = log_format
        self.logger = self.setup_logging()

    def setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(level=logging.INFO, format=self.log_format)
        return logging.getLogger(__name__)

    def get_logger(self) -> logging.Logger:
        return self.logger
