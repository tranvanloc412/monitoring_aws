import logging
import sys


class LoggerSetup:
    def __init__(self, log_format: str):
        self.log_format = log_format
        self.setup_logging()

    def setup_logging(self) -> None:
        """Setup logging configuration on the root logger."""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        if not root_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(self.log_format)
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)

    def get_logger(self, name: str) -> logging.Logger:
        return logging.getLogger(name) if name else logging.getLogger()
