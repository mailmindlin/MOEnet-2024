from typedef.cfg import DataLogConfig
from pathlib import Path
import errno, stat, os, logging

_WINERROR_NOT_READY = 21  # drive exists but is not accessible
_WINERROR_INVALID_NAME = 123  # fix for bpo-35306
_WINERROR_CANT_RESOLVE_FILENAME = 1921  # broken symlink pointing to itself

# EBADF - guard against macOS `stat` throwing EBADF
_IGNORED_ERRNOS = (errno.ENOENT, errno.ENOTDIR, errno.EBADF, errno.ELOOP)
_IGNORED_WINERRORS = (
    _WINERROR_NOT_READY,
    _WINERROR_INVALID_NAME,
    _WINERROR_CANT_RESOLVE_FILENAME)

def _ignore_error(exception: OSError):
    return (getattr(exception, 'errno', None) in _IGNORED_ERRNOS or
            getattr(exception, 'winerror', None) in _IGNORED_WINERRORS)

class DataLogManager:
    "Helper for data logs"
    def __init__(self, config: DataLogConfig, log: logging.Logger | None) -> None:
        self.config = config
        self.log = log or logging.getLogger('datalog')
    
    @property
    def folder(self):
        "Log folder"
        if logDir := self.config.folder:
            return logDir
    
    def _folder_stat(self):
        if folder := self.folder:
            try:
                return folder.stat()
            except OSError as e:
                if not _ignore_error(e):
                    raise
                # Path doesn't exist or is a broken symlink
                # (see http://web.archive.org/web/20200623061726/https://bitbucket.org/pitrou/pathlib/issues/12/ )
                return None
            except ValueError:
                # Non-encodable path
                return None
        return None
    
    def free_space(self):

        return 0
    
    @property
    def enabled(self):
        "Are datalogs enabled?"
        if not self.config.enabled:
            return False
        if st := self._folder_stat():
            if not stat.S_ISDIR(st.st_mode):
                return False
        return True
    
    def _might_cleanup(self):
        "Might this DataLogManager clean up logs under any circumstances?"
        if not self.enabled:
            return False
        if not self.config.cleanup:
            return False
        return True
    
    def should_cleanup(self):
        if not self.config.cleanup:
            return False
        
    
    def log_files(self, include_current: bool = True):
        """
        Enumerate datalog files
        
        Parameters
        ----------
        :param include_current: Should we include files that are 
        
        """
        folder = self.folder
        if not folder:
            return
        
        for file in folder.glob("FRC_*.wpilog"):
            if include_current or (not file.name.startswith('FRC_TBD_')):
                yield file
    
    def start(self):
        # This is inefficient, but should only be called once
        while self.should_cleanup():
            # Delete oldest FRC_*.wpilog files (ignore FRC_TBD_*.wpilog as we just created one)
            prev_files = sorted(self.log_files(include_current=False), key=os.path.getmtime)
            print(f"Deleting file {prev_files[0]}")
            prev_files[0].unlink()
        
        if (free_space_req := self.config.free_space) is not None:
            free_space = self.free_space()
            if free_space < 2 * free_space_req:
                print("Warning: Device has {free_space} remaining!")