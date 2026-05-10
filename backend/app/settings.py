import os
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


class Settings:
    def __init__(self) -> None:
        self.upload_root = Path(os.getenv("UPLOAD_DIR", "/data/uploads"))
        self.max_upload_mb = _env_int("MAX_UPLOAD_MB", 50)

    @property
    def raw_dir(self) -> Path:
        return self.upload_root / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.upload_root / "processed"


settings = Settings()

