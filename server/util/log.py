import logging
from typing import Optional

def child_logger(name: str, parent: Optional[logging.Logger] = None) -> logging.Logger:
    if parent is not None:
        return parent.getChild(name)
    else:
        return logging.getLogger(name)

class ColorFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    green = '\x1b[0;32m'
    reset = "\x1b[0m"
    formatp = "[%(levelname)s]%(name)s:%(message)s"

    FORMATS = {
        logging.DEBUG: grey + formatp + reset,
        logging.INFO: green + formatp + reset,
        logging.WARNING: yellow + formatp + reset,
        logging.ERROR: red + formatp + reset,
        logging.CRITICAL: bold_red + formatp + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)