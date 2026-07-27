from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, QWidget
from PySide6.QtCore import Qt, Signal
from ui.file_utils import open_local_path
from ui.image_loader import load_scaled_pixmap

class ThumbnailCard(QFrame):
    clicked = Signal(str, dict) # emits (image_path, metadata)

    def __init__(self, image_path: str, metadata: dict, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.metadata = metadata
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #ffffff; border-radius: 4px; color: #1d1d1f;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Header with CheckBox
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(2, 0, 2, 0)
        header_layout.setSpacing(0)

        self.cb = QCheckBox()
        self.cb.setStyleSheet("QCheckBox::indicator { width: 18px; height: 18px; }")
        header_layout.addStretch()
        header_layout.addWidget(self.cb)
        layout.addWidget(header)

        # Image Thumbnail
        self.thumb = QLabel()
        self.thumb.setFixedSize(100, 100)
        self.thumb.setStyleSheet("background-color: #ffffff;")
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        pix = load_scaled_pixmap(self.image_path, 100, 100)
        if not pix.isNull():
            self.thumb.setPixmap(pix)
        layout.addWidget(self.thumb, 0, Qt.AlignCenter)

        # Title Label
        is_fav = self.metadata.get("favorite", False)
        fav_star = "⭐ " if is_fav else ""
        title_text = f"{fav_star}{self.metadata.get('style', '')}"
        self.title_lbl = QLabel(title_text)
        self.title_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #1d1d1f;")
        self.title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.title_lbl, 0, Qt.AlignCenter)

    def mousePressEvent(self, event):
        self.clicked.emit(self.image_path, self.metadata)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        open_local_path(self.image_path)
        super().mouseDoubleClickEvent(event)

    def set_selected(self, selected: bool):
        if selected:
            self.setStyleSheet("background-color: #007aff; border-radius: 4px; color: #ffffff;")
            self.title_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #ffffff;")
        else:
            self.setStyleSheet("background-color: #ffffff; border-radius: 4px; color: #1d1d1f;")
            self.title_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #1d1d1f;")
