import logging
from wpiutil.log import DataLog, StringLogEntry


class PyToNtHandler(logging.Handler):
    "Forward Python logs to DataLog"
    def __init__(self, log: DataLog, path: str = 'log', level: 'logging._Level' = 0) -> None:
        super().__init__(level)
        self.entry = StringLogEntry(log, path)
        self.setFormatter(logging.Formatter('[%(levelname)s]%(name)s:%(message)s'))
    
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.entry.append(msg)
        except RecursionError:  # See issue 36272
            raise
        except Exception:
            self.handleError(record)
    
    def close(self) -> None:
         self.entry.finish()
         del self.entry

         return super().close()