import logging
import json
from pythonjsonlogger import jsonlogger

class Logger:
    """
    Custom logger for JSON-formatted application logging.
    """
    def __init__(self, name="app", level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self._configure_logging()

    def _configure_logging(self):
        """
        Configure logging format and handler for JSON logs.
        """
        # Define JSON log format
        log_format = {
            "timestamp": "%(asctime)s",
            "name": "%(name)s",
            "level": "%(levelname)s",
            "message": "%(message)s",
        }
        formatter = jsonlogger.JsonFormatter(json.dumps(log_format))

        # Stream handler for console output
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(handler)

    def info(self, message, **kwargs):
        """
        Log an informational message with optional context.
        """
        self.logger.info(message, extra={"context": kwargs})

    def error(self, message, **kwargs):
        """
        Log an error message with optional context.
        """
        self.logger.error(message, extra={"context": kwargs})

    def warning(self, message, **kwargs):
        """
        Log a warning message with optional context.
        """
        self.logger.warning(message, extra={"context": kwargs})