"""Runtime settings, read from environment variables named in VULTR_DEPLOYMENT.md."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_env: str
    public_origin: str
    database_url: str
    object_store_root: Path

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            app_env=os.environ.get("APP_ENV", "demo"),
            public_origin=os.environ.get("PUBLIC_ORIGIN", "http://localhost:8000"),
            database_url=os.environ.get(
                "DATABASE_URL", "postgresql://ledgerflow@localhost:5432/ledgerflow"
            ),
            object_store_root=Path(os.environ.get("OBJECT_STORE_ROOT", "./data/objects")),
        )
