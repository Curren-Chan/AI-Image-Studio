import logging
import os

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def open_local_path(path: str) -> bool:
    if not path or not os.path.exists(path):
        return False
    try:
        if hasattr(os, "startfile"):
            os.startfile(path)
            return True
    except OSError as exc:
        logging.warning("Native open failed for %s: %s", path, exc)
    return bool(QDesktopServices.openUrl(QUrl.fromLocalFile(path)))
