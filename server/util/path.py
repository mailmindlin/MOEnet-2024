from pathlib import Path
import os.path

def resolve_path(base: Path | None, relpart: str | Path):
    if isinstance(relpart, str):
        relpart = Path(relpart)
    
    if relpart.is_absolute():
        return relpart
    relpart = Path(os.path.expanduser(relpart))
    if relpart.is_absolute():
        return relpart
    elif base is None:
        raise ValueError(f'Unable to resolve relative path {relpart}')
    else:
        return (base / relpart).resolve()