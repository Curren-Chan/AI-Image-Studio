import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFrame, QMessageBox
from PySide6.QtCore import Qt, Signal
from core.event_bus import event_bus
from ui.file_utils import open_local_path
from ui.image_loader import load_scaled_pixmap

class ClickableLabel(QLabel):
    doubleClicked = Signal()
    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)

class PreviewPanel(QWidget):
    image_dropped = Signal(str) # Emitted when an image path is dropped

    # Keep experimental preview actions in one removable list.  The toolbar,
    # callbacks, and labels below are intentionally isolated from core preview
    # rendering so either action can be removed without side effects.
    OPTIONAL_ACTIONS = ("regenerate", "retake")

    def __init__(self, coordinator, parent=None):
        super().__init__(parent)
        self.coordinator = coordinator
        self.current_image_path = None
        self.current_metadata = {}
        self.init_ui()
        self.setAcceptDrops(True)
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # 1. Image Preview Frame
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet("background-color: #1c1c1e; border-radius: 6px;")
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(5, 5, 5, 5)
        
        self.preview_canvas = ClickableLabel("Drag & Drop images here or click Generate to view outputs.")
        self.preview_canvas.setStyleSheet("color: #8e8e93; font-size: 13px; font-weight: bold;")
        self.preview_canvas.setAlignment(Qt.AlignCenter)
        self.preview_canvas.setFixedSize(450, 450)
        self.preview_canvas.doubleClicked.connect(self.on_canvas_double_clicked)
        preview_layout.addWidget(self.preview_canvas)
        layout.addWidget(self.preview_frame)
        
        # 2. Control Toolbar
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(10)
        
        self.favorite_btn = QPushButton("⭐ Mark Favorite")
        self.favorite_btn.clicked.connect(self.toggle_favorite)
        toolbar_layout.addWidget(self.favorite_btn)
        
        if "regenerate" in self.OPTIONAL_ACTIONS:
            self.regenerate_btn = QPushButton("🔁 再生成")
            self.regenerate_btn.setToolTip("Generate again using the current input settings.")
            self.regenerate_btn.clicked.connect(self.regenerate_current_settings)
            toolbar_layout.addWidget(self.regenerate_btn)

        if "retake" in self.OPTIONAL_ACTIONS:
            self.retake_btn = QPushButton("🔄 設定を復元して再生成")
            self.retake_btn.setToolTip("Restore this image's saved settings, then generate again.")
            self.retake_btn.clicked.connect(self.retake_generation)
            toolbar_layout.addWidget(self.retake_btn)
        
        self.open_folder_btn = QPushButton("📁 Open Folder")
        self.open_folder_btn.clicked.connect(self.open_folder)
        toolbar_layout.addWidget(self.open_folder_btn)

        if hasattr(self, "regenerate_btn"):
            self.regenerate_btn.setEnabled(False)
        if hasattr(self, "retake_btn"):
            self.retake_btn.setEnabled(False)
        
        layout.addWidget(toolbar)
        
        # 3. Parameters text detail log
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setPlaceholderText("Generation log details will be displayed here.")
        self.log_display.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; background-color: #2c2c2e; color: #34c759;")
        layout.addWidget(self.log_display, 1)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                self.image_dropped.emit(file_path)

    def set_image(self, image_path: str, metadata: dict):
        self.current_image_path = image_path
        self.current_metadata = metadata
        
        pix = load_scaled_pixmap(image_path, 450, 450)
        if not pix.isNull():
            self.preview_canvas.setPixmap(pix)
        else:
            self.preview_canvas.setText("Failed to load image preview.")
            
        # Update details log
        translation_rule = metadata.get("style", "プリセット無し")
        style_preset = metadata.get("style_preset", "プリセット無し")
        size = metadata.get("size", "1024x1024")
        quality = metadata.get("quality", "Medium")
        try:
            cost = float(metadata.get("cost", 0.0))
        except (TypeError, ValueError):
            cost = 0.0
        model_name = metadata.get("model_name", "N/A")
        provider = metadata.get("provider", "N/A")
        
        expert_params = metadata.get("expert_params", "")
        expert_str = f"\nExpert Params: {expert_params}" if expert_params else ""
        
        log_str = (
            f"File: {os.path.basename(image_path)}\n"
            f"Model: {model_name} ({provider})\n"
            f"Translation Rule: {translation_rule}  |  Style Preset: {style_preset}\n"
            f"Size: {size}  |  Quality: {quality}  |  Cost: ${cost:.5f}\n"
            f"Prompt (JP): {metadata.get('prompt_jp', '')}\n"
            f"Prompt (EN): {metadata.get('prompt_en', '')}\n"
            f"Negative: {metadata.get('negative_prompt', '')}{expert_str}"
        )
        self.log_display.setPlainText(log_str)
        
        # Update star button
        is_fav = metadata.get("favorite", False)
        self.favorite_btn.setText("⭐ Starred (Favorite)" if is_fav else "⭐ Mark Favorite")
        if hasattr(self, "regenerate_btn"):
            self.regenerate_btn.setEnabled(True)
        if hasattr(self, "retake_btn"):
            self.retake_btn.setEnabled(True)

    def toggle_favorite(self):
        if not self.current_image_path:
            return
            
        # Call HistoryService via coordinator
        new_state = self.coordinator.history_service.toggle_favorite(self.current_image_path)
        self.current_metadata["favorite"] = new_state
        self.favorite_btn.setText("⭐ Starred (Favorite)" if new_state else "⭐ Mark Favorite")
        
        # Refresh gallery list
        event_bus.gallery_refresh_requested.emit()

    def retake_generation(self):
        if not self.current_metadata:
            return
            
        # Emit context loaded signal to update prompt panel inputs
        event_bus.context_changed.emit(self.current_metadata)
        
        model_id = self.current_metadata.get("model_id", "openai-gpt-image-2")
        emit_dict = {
            "prompt_jp": self.current_metadata.get("prompt_jp", ""),
            "translation_rule": self.current_metadata.get("style", "Standard"),
            "style_preset": self.current_metadata.get("style_preset", "プリセット無し"),
            "size": self.current_metadata.get("size", "1024x1024"),
            "negative_prompt": self.current_metadata.get("negative_prompt", ""),
            "quality": self.current_metadata.get("quality", "standard"),
            "batch_count": 1,
            "model_id": model_id,
            "expert_params": self.current_metadata.get("expert_params"),
            "mask_path": None
        }
        
        is_edit = False
        main_win = self.window()
        if hasattr(main_win, "prompt_panel") and hasattr(main_win.prompt_panel, "btn_edit_mode"):
            is_edit = main_win.prompt_panel.btn_edit_mode.isChecked()
            
        from api.model_registry import MODEL_REGISTRY
        if MODEL_REGISTRY.get(model_id, {}).get("category") == "img_edit":
            is_edit = True
            
        if is_edit and self.current_image_path:
            emit_dict["image_path"] = self.current_image_path
        
        # Trigger immediate generation request
        event_bus.generation_requested.emit(emit_dict)

    def regenerate_current_settings(self):
        """Delegate to the current prompt form; no historical settings are restored."""
        main_win = self.window()
        if hasattr(main_win, "prompt_panel"):
            main_win.prompt_panel.request_generation()

    def open_folder(self):
        out_dir = self.coordinator.generation_service.output_dir
        if not open_local_path(out_dir):
            QMessageBox.critical(self, "Error", f"Could not open outputs folder '{out_dir}'.")

    def clear_preview(self):
        self.current_image_path = None
        self.current_metadata = {}
        self.preview_canvas.clear()
        self.preview_canvas.setText("Drag & Drop images here or click Generate to view outputs.")
        self.log_display.clear()
        self.favorite_btn.setText("⭐ Mark Favorite")
        if hasattr(self, "regenerate_btn"):
            self.regenerate_btn.setEnabled(False)
        if hasattr(self, "retake_btn"):
            self.retake_btn.setEnabled(False)

    def on_canvas_double_clicked(self):
        if self.current_image_path and not open_local_path(self.current_image_path):
            QMessageBox.warning(self, "Open failed", "Could not open the current image.")
