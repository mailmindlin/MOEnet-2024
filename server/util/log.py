import logging
from typing import Optional

def child_logger(name: str, parent: Optional[logging.Logger] = None) -> logging.Logger:
    if parent is not None:
        return parent.getChild(name)
    else:
        return logging.getLogger(name)
