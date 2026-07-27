import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, 
    QFileDialog, QMessageBox, QLabel, QGridLayout,
    QSplitter, QTextEdit, QComboBox
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QImage, QPixmap
from core.event_bus import event_bus
from ui.file_utils import open_local_path
from ui.image_loader import load_scaled_pixmap
from ui.widgets.thumbnail_card import ThumbnailCard

from ui.panels.preview_panel import ClickableLabel


class GalleryLoaderWorker(QThread):
    data_loaded = Signal(list)

    def __init__(self, coordinator, sort_order: str = "newest", parent=None):
        super().__init__(parent)
        self.coordinator = coordinator
        self.sort_order = sort_order

    def run(self):
        project_id = self.coordinator.project_service.get_active_project_id()
        history = self.coordinator.history_service.get_history(
            project_id=project_id,
            search_query="",
            favorite_only=False,
            sort_order=self.sort_order,
        )
        loaded_items = []
        for item in history:
            image_path = item["image_path"]
            if not os.path.isfile(image_path):
                continue
            qimg = QImage(image_path)
            if not qimg.isNull():
                qimg = qimg.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            loaded_items.append((image_path, item["metadata"], qimg))
        self.data_loaded.emit(loaded_items)


class GalleryPanel(QWidget):
    context_load_requested = Signal(str, dict)
    loading_started = Signal()
    loading_finished = Signal()

    def __init__(self, coordinator, parent=None):
        super().__init__(parent)
        self.coordinator = coordinator
        self.cards = []
        self.selected_card = None
        self.current_image_path = None
        self._refreshing = False
        self._refresh_pending = False
        self._deleting = False
        self._initialized = False
        self._loading = False
        self.worker = None
        self.init_ui()
        
        # Subscribe to EventBus
        event_bus.gallery_refresh_requested.connect(self.on_gallery_refresh_requested)
        event_bus.project_changed.connect(self.on_project_changed)

    def ensure_initialized(self):
        """Lazy initializer called when tab is first shown if background load was not started."""
        if not self._initialized and not self._loading:
            self.start_async_load()

    def start_async_load(self):
        """Starts loading gallery items in a background thread."""
        if self._initialized or self._loading:
            return
        self._loading = True
        self.loading_started.emit()
        sort_order = self.sort_combo.currentData() if hasattr(self, "sort_combo") else "newest"
        self.worker = GalleryLoaderWorker(self.coordinator, sort_order=sort_order, parent=self)
        self.worker.data_loaded.connect(self._on_async_data_loaded)
        self.worker.start()

    def _on_async_data_loaded(self, loaded_items):
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                self.grid_layout.removeWidget(widget)
                widget.deleteLater()

        self._clear_current_selection()
        self.cards.clear()

        for index, (image_path, metadata, qimg) in enumerate(loaded_items):
            pixmap = QPixmap.fromImage(qimg) if qimg and not qimg.isNull() else None
            card = ThumbnailCard(image_path, metadata, self.grid_widget, pixmap=pixmap)
            card.clicked.connect(self.on_card_clicked)
            self.cards.append(card)
            self.grid_layout.addWidget(card, index // 3, index % 3)

        self._initialized = True
        self._loading = False
        self.loading_finished.emit()

    def on_gallery_refresh_requested(self):
        if self._initialized:
            self.refresh_gallery()

    def on_sort_changed(self):
        """Re-sort current cards in memory for instant feedback."""
        if not self.cards:
            return
        sort_mode = self.sort_combo.currentData()
        if sort_mode == "newest":
            self.cards.sort(key=lambda c: str(c.metadata.get("timestamp", "")), reverse=True)
        elif sort_mode == "oldest":
            self.cards.sort(key=lambda c: str(c.metadata.get("timestamp", "")), reverse=False)
        elif sort_mode == "favorite":
            self.cards.sort(key=lambda c: (0 if c.metadata.get("favorite", False) else 1, str(c.metadata.get("timestamp", ""))), reverse=False)
        elif sort_mode == "filename":
            self.cards.sort(key=lambda c: str(c.metadata.get("filename", "")).lower(), reverse=False)

        self.rearrange_grid()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Splitter Layout (Left: Grid, Right: Details)
        splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel (Grid & Bulk Actions)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Top Sort Toolbar
        sort_bar = QWidget()
        sort_layout = QHBoxLayout(sort_bar)
        sort_layout.setContentsMargins(0, 0, 0, 0)
        sort_layout.setSpacing(8)

        lbl_sort = QLabel("並び替え (Sort):")
        lbl_sort.setStyleSheet("font-weight: bold; color: #8e8e93;")
        sort_layout.addWidget(lbl_sort)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("📅 日時が新しい順 (Newest First)", "newest")
        self.sort_combo.addItem("📅 日時が古い順 (Oldest First)", "oldest")
        self.sort_combo.addItem("⭐ お気に入り優先 (Favorites First)", "favorite")
        self.sort_combo.addItem("🔤 ファイル名順 (Name A-Z)", "filename")
        self.sort_combo.setFixedHeight(32)
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        sort_layout.addWidget(self.sort_combo, 1)
        sort_layout.addStretch()

        left_layout.addWidget(sort_bar)
        
        # Scroll Area for Thumbnails Grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #1c1c1e; border-radius: 4px;")
        
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background-color: #1c1c1e;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.scroll_area.setWidget(self.grid_widget)
        left_layout.addWidget(self.scroll_area)
        
        # Bulk Actions Toolbar
        actions_bar = QWidget()
        actions_layout = QHBoxLayout(actions_bar)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(10)
        
        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(self.select_all)
        actions_layout.addWidget(self.btn_select_all)
        
        self.btn_deselect_all = QPushButton("Clear Selection")
        self.btn_deselect_all.clicked.connect(self.deselect_all)
        actions_layout.addWidget(self.btn_deselect_all)
        
        self.btn_export = QPushButton("📤 Bulk Export Selected")
        self.btn_export.clicked.connect(self.bulk_export)
        actions_layout.addWidget(self.btn_export)
        
        self.btn_delete = QPushButton("🗑️ Delete Selected")
        self.btn_delete.clicked.connect(self.bulk_delete)
        self.btn_delete.setStyleSheet("background-color: #ff3b30; color: white;")
        actions_layout.addWidget(self.btn_delete)
        
        left_layout.addWidget(actions_bar)
        splitter.addWidget(left_widget)
        
        # Right Panel (Preview & Metadata Detail Dump)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        
        # Image Preview Label
        self.preview_lbl = ClickableLabel("Select an image to preview")
        self.preview_lbl.setAlignment(Qt.AlignCenter)
        self.preview_lbl.setFixedSize(450, 450)
        self.preview_lbl.setStyleSheet(
            "QLabel { border: 1px solid #2c2c2e; border-radius: 6px; background-color: #121212; color: #8e8e93; font-size: 11px; }"
        )
        self.preview_lbl.doubleClicked.connect(self.on_preview_double_clicked)
        right_layout.addWidget(self.preview_lbl, 0, Qt.AlignCenter)
        
        right_layout.addWidget(QLabel("Metadata Log Detail Dump:"))
        
        self.details_box = QTextEdit()
        self.details_box.setReadOnly(True)
        self.details_box.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        right_layout.addWidget(self.details_box)
        
        self.btn_load_context = QPushButton("コンテキストを読み込む（入力に反映）")
        self.btn_load_context.setStyleSheet("background-color: #34c759; color: white; font-weight: bold;")
        self.btn_load_context.clicked.connect(self.load_selected_context)
        self.btn_load_context.setEnabled(False)
        right_layout.addWidget(self.btn_load_context)
        
        splitter.addWidget(right_widget)
        layout.addWidget(splitter)
        
        # Initial ratio: left 55%, right 45% (wider details)
        splitter.setSizes([600, 480])

    def refresh_gallery(self):
        if self._refreshing or self._deleting:
            self._refresh_pending = True
            return
        self._refreshing = True
        try:
            for i in reversed(range(self.grid_layout.count())):
                widget = self.grid_layout.itemAt(i).widget()
                if widget:
                    self.grid_layout.removeWidget(widget)
                    widget.deleteLater()

            self._clear_current_selection()
            self.cards.clear()

            project_id = self.coordinator.project_service.get_active_project_id()
            sort_order = self.sort_combo.currentData() if hasattr(self, "sort_combo") else "newest"
            history = self.coordinator.history_service.get_history(
                project_id=project_id,
                search_query="",
                favorite_only=False,
                sort_order=sort_order,
            )

            for item in history:
                image_path = item["image_path"]
                if not os.path.isfile(image_path):
                    continue
                card = ThumbnailCard(image_path, item["metadata"], self.grid_widget)
                card.clicked.connect(self.on_card_clicked)
                index = len(self.cards)
                self.cards.append(card)
                self.grid_layout.addWidget(card, index // 3, index % 3)
        finally:
            self._refreshing = False
            if self._refresh_pending and not self._deleting:
                self._refresh_pending = False
                self.refresh_gallery()

    def on_card_clicked(self, image_path: str, metadata: dict):
        clicked_card = None
        for card in self.cards:
            if card.image_path == image_path:
                clicked_card = card
                break
                
        if clicked_card:
            if self.selected_card and self.selected_card in self.cards:
                self.selected_card.set_selected(False)
            self.selected_card = clicked_card
            self.selected_card.set_selected(True)
            self.current_image_path = image_path
            self.update_preview_image()
            self.display_metadata(metadata)
            self.btn_load_context.setEnabled(True)
        else:
            self._clear_current_selection()
            
    def display_metadata(self, meta: dict):
        expert_params = meta.get("expert_params", "")
        expert_str = f"Expert Params: {expert_params}\n" if expert_params else ""
        
        try:
            cost = float(meta.get("cost", 0.0))
        except (TypeError, ValueError):
            cost = 0.0

        detail_str = (
            f"ID: {meta.get('id', 'N/A')}\n"
            f"Timestamp: {meta.get('timestamp', '')}\n"
            f"Filename: {meta.get('filename', '')}\n"
            f"Model: {meta.get('model_name', 'N/A')}\n"
            f"Provider: {meta.get('provider', 'N/A')}\n"
            f"Translation Rule: {meta.get('style', '')}\n"
            f"Style Preset: {meta.get('style_preset', 'プリセット無し')}\n"
            f"Size: {meta.get('size', '')}\n"
            f"Quality: {meta.get('quality', '')}\n"
            f"Estimated Cost: ${cost:.5f}\n"
            f"Favorite: {'Yes' if meta.get('favorite') else 'No'}\n"
            f"{expert_str}\n"
            f"--- PROMPT (JP) ---\n{meta.get('prompt_jp', '')}\n\n"
            f"--- PROMPT (EN) ---\n{meta.get('prompt_en', '')}\n\n"
            f"--- NEGATIVE PROMPT ---\n{meta.get('negative_prompt', '')}"
        )
        self.details_box.setPlainText(detail_str)

    def load_selected_context(self):
        if not self.selected_card:
            return
        meta = self.selected_card.metadata.copy()
        meta["switch_tab"] = 0

        self.context_load_requested.emit(self.selected_card.image_path, meta)

    def on_project_changed(self, project_id: int):
        if self._initialized:
            self.refresh_gallery()

    def select_all(self):
        for card in self.cards:
            card.cb.setChecked(True)
        self._clear_current_selection()

    def deselect_all(self):
        for card in self.cards:
            card.cb.setChecked(False)
        self._clear_current_selection()

    def bulk_delete(self):
        if self._deleting:
            return
        selected_cards = [c for c in self.cards if c.cb.isChecked()]
        if not selected_cards:
            QMessageBox.information(self, "Delete", "No images selected.")
            return
            
        ret = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete {len(selected_cards)} selected image(s)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ret == QMessageBox.Yes:
            paths = [str(card.image_path) for card in selected_cards]
            self._deleting = True
            self.btn_delete.setEnabled(False)
            try:
                deleted_count = sum(
                    1
                    for path in paths
                    if self.coordinator.gallery_service.delete_image_record(path)
                )
            finally:
                self._deleting = False
                self.btn_delete.setEnabled(True)
                self._refresh_pending = False
                self.refresh_gallery()

            if deleted_count == len(paths):
                event_bus.status_updated.emit(
                    f"Deleted {deleted_count} image(s) successfully."
                )
                QMessageBox.information(
                    self, "Deleted", f"Deleted {deleted_count} image(s) successfully."
                )
            else:
                failed_count = len(paths) - deleted_count
                event_bus.status_updated.emit(
                    f"Deleted {deleted_count} image(s); {failed_count} failed."
                )
                QMessageBox.warning(
                    self,
                    "Delete incomplete",
                    f"Deleted {deleted_count} image(s). {failed_count} item(s) were kept because deletion failed.",
                )

    def rearrange_grid(self):
        """Rearrange remaining cards in grid layout without destroying/reloading QPixmaps."""
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                self.grid_layout.removeWidget(item.widget())
                
        cols = 3
        row = 0
        col = 0
        for card in self.cards:
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def bulk_export(self):
        selected_cards = [c for c in self.cards if c.cb.isChecked()]
        if not selected_cards:
            QMessageBox.information(self, "Export", "No images selected.")
            return
            
        export_dir = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if export_dir:
            paths = [c.image_path for c in selected_cards]
            count = self.coordinator.gallery_service.bulk_export(paths, export_dir)
            QMessageBox.information(self, "Export Complete", f"Successfully exported {count} of {len(paths)} images.")

    def update_preview_image(self):
        if not hasattr(self, 'preview_lbl'):
            return
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            self.preview_lbl.clear()
            self.preview_lbl.setText("Select an image to preview")
            return
            
        pixmap = load_scaled_pixmap(
            self.current_image_path,
            max(100, self.preview_lbl.width() - 4),
            max(100, self.preview_lbl.height() - 4),
        )
        if not pixmap.isNull():
            self.preview_lbl.setPixmap(pixmap)
        else:
            self.preview_lbl.clear()
            self.preview_lbl.setText("Error loading image preview")

    def on_preview_double_clicked(self):
        if self.current_image_path and os.path.exists(self.current_image_path):
            if not open_local_path(self.current_image_path):
                QMessageBox.warning(self, "Open failed", "Could not open the selected image.")

    def _clear_current_selection(self):
        if self.selected_card and self.selected_card in self.cards:
            self.selected_card.set_selected(False)
        self.selected_card = None
        self.current_image_path = None
        if hasattr(self, "preview_lbl"):
            self.preview_lbl.clear()
            self.preview_lbl.setText("Select an image to preview")
        if hasattr(self, "details_box"):
            self.details_box.clear()
        if hasattr(self, "btn_load_context"):
            self.btn_load_context.setEnabled(False)
