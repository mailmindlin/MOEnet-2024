from typedef.cfg import DataLogConfig
from pathlib import Path
import errno, stat, os

_WINERROR_NOT_READY = 21  # drive exists but is not accessible
_WINERROR_INVALID_NAME = 123  # fix for bpo-35306
_WINERROR_CANT_RESOLVE_FILENAME = 1921  # broken symlink pointing to itself

# EBADF - guard against macOS `stat` throwing EBADF
_IGNORED_ERRNOS = (errno.ENOENT, errno.ENOTDIR, errno.EBADF, errno.ELOOP)
_IGNORED_WINERRORS = (
    _WINERROR_NOT_READY,
    _WINERROR_INVALID_NAME,
    _WINERROR_CANT_RESOLVE_FILENAME)

def _ignore_error(exception):
    return (getattr(exception, 'errno', None) in _IGNORED_ERRNOS or
            getattr(exception, 'winerror', None) in _IGNORED_WINERRORS)

class DataLogManager:
    "Helper for data logs"
    def __init__(self, config: DataLogConfig) -> None:
        self.config = config
    
    @property
    def folder(self):
        if logDir := self.config.folder:
            return logDir
    
    def folder_stat(self):
        if folder := self.folder:
            try:
                return folder.is_dir.stat()
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
    
    def enabled(self):
        if not self.config.enabled:
            return False
        if st := self.folder_stat():
            if not stat.S_ISDIR(st.st_mode):
                return False
        return True
    
    def should_cleanup(self):
        if not self.config.cleanup:
            return False
        self.config.f
    
    def log_files(self, include_current: bool = True) -> list[Path]:
        folder = self.folder
        if not folder:
            return []
        res = list()
        for file in folder.glob("FRC_*.wpilog"):
            if (not include_current) and file.name.startswith('FRC_TBD_'):
                continue
            res.append(file)
        return res
    
    def start(self):
        # This is inefficient, but should only be called once
        while self.should_cleanup():
            # Delete oldest FRC_*.wpilog files (ignore FRC_TBD_*.wpilog as we just created one)
            prev_files = self.log_files(include_current=False)
            prev_files.sort(key=os.path.getmtime)
            print(f"Deleting file {prev_files[0]}")
            prev_files[0].unlink()
        
        if (free_space_req := self.config.free_space) is not None:
            free_space = self.free_space()
            if free_space < 2 * free_space_req:
                print("Warning: Device has {free_space} remaining!")