import logging
import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImageReader, QPixmap


MAX_SOURCE_PIXELS = 100_000_000


def load_scaled_pixmap(path: str, width: int, height: int) -> QPixmap:
    """Decode an image at display size and reject oversized/corrupt sources."""
    if not path or not os.path.isfile(path):
        return QPixmap()
    reader = QImageReader(path)
    reader.setDecideFormatFromContent(True)
    reader.setAutoTransform(True)
    source_size = reader.size()
    if not source_size.isValid():
        logging.warning("Could not read image dimensions: %s", path)
        return QPixmap()
    if source_size.width() * source_size.height() > MAX_SOURCE_PIXELS:
        logging.warning("Refusing oversized image preview: %s", path)
        return QPixmap()
    target_size = source_size.scaled(
        QSize(max(1, width), max(1, height)), Qt.AspectRatioMode.KeepAspectRatio
    )
    reader.setScaledSize(target_size)
    image = reader.read()
    if image.isNull():
        logging.warning("Could not decode image preview %s: %s", path, reader.errorString())
        return QPixmap()
    return QPixmap.fromImage(image)
