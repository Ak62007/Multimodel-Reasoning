"""Centralised logging configuration for the pipeline.

`configure_logging` installs a rich console handler and optionally a file sink.
Idempotent — safe to call multiple times in tests / repeated job runs.
"""

from __future__ import annotations

import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

_CONFIGURED = False


def configure_logging(
    level: int | str = logging.INFO,
    *,
    log_file: Path | str | None = None,
    force: bool = False,
) -> None:
    """Install handlers on the root logger.

    Subsequent calls are no-ops unless `force=True`. Pass `log_file` to also write
    to disk (per-job log capture for the backend's `/api/jobs/{id}/logs` endpoint).
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    root = logging.getLogger()
    if force:
        for h in list(root.handlers):
            root.removeHandler(h)

    root.setLevel(level)

    console = Console(stderr=True)
    root.addHandler(
        RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            markup=False,
        )
    )

    if log_file is not None:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        root.addHandler(fh)

    # Quiet down noisy third-party loggers
    for noisy in ("urllib3", "filelock", "mediapipe"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
