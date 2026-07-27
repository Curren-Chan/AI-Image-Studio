from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QMessageBox, QLabel, QFrame
from PySide6.QtCore import Qt, Slot, QTimer

from core.event_bus import event_bus
from ui.panels.prompt_panel import PromptPanel
from ui.panels.preview_panel import PreviewPanel
from ui.panels.gallery_panel import GalleryPanel
from ui.panels.project_panel import ProjectPanel
from ui.panels.settings_panel import SettingsPanel
from ui.panels.status_panel import StatusPanel
from ui.widgets.generation_action_bar import GenerationActionBar
from core.version import APP_VERSION
from ui.panels.tips_panel import TipsPanel
from ui.panels.queue_panel import QueuePanel
from ui.panels.model_catalog_panel import ModelCatalogPanel


class MainWindow(QMainWindow):
    def __init__(self, coordinator):
        super().__init__()
        self.coordinator = coordinator
        self._shutdown_pending = False
        self._shutdown_complete = False
        self._shutdown_timer = QTimer(self)
        self._shutdown_timer.setInterval(100)
        self._shutdown_timer.timeout.connect(self._poll_shutdown)
        
        self.setWindowTitle(f"AI Image Studio Ver{APP_VERSION}")
        self.resize(1200, 1150)
        self.setMinimumSize(1000, 950)
        
        self.init_ui()
        self.apply_theme(self.coordinator.settings_service.get_setting("theme", "Dark"))
        
        # Subscribe to EventBus
        event_bus.generation_requested.connect(self.on_generation_requested)
        event_bus.theme_changed.connect(self.apply_theme)
        event_bus.context_changed.connect(self.on_context_changed_generic)
        event_bus.image_generated.connect(self.on_image_generated)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        header = QFrame()
        header.setObjectName("appHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 20, 14)
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(1)
        title = QLabel("AI Image Studio")
        title.setObjectName("appTitle")
        subtitle = QLabel("Create, refine, and organize your visual ideas")
        subtitle.setObjectName("appSubtitle")
        brand_layout.addWidget(title)
        brand_layout.addWidget(subtitle)
        header_layout.addLayout(brand_layout)
        header_layout.addStretch()
        
        header_layout.addSpacing(20)
        
        workspace_hint = QLabel("WORKSPACE")
        workspace_hint.setObjectName("headerPill")
        header_layout.addWidget(workspace_hint, 0, Qt.AlignVCenter)
        main_layout.addWidget(header)
        
        # Main Tab Widget
        self.tabs = QTabWidget()

        # Panel 1: txt2img (Prompt + Preview side by side)
        txt2img_widget = QWidget()
        generation_page_layout = QVBoxLayout(txt2img_widget)
        generation_page_layout.setContentsMargins(0, 0, 0, 0)
        generation_page_layout.setSpacing(10)
        txt2img_content = QWidget(txt2img_widget)
        txt2img_layout = QHBoxLayout(txt2img_content)
        txt2img_layout.setContentsMargins(10, 10, 10, 10)
        txt2img_layout.setSpacing(20)
        
        self.prompt_panel = PromptPanel(self.coordinator, txt2img_widget)
        self.preview_panel = PreviewPanel(self.coordinator, txt2img_widget)
        
        txt2img_layout.addWidget(self.prompt_panel, 3)
        txt2img_layout.addWidget(self.preview_panel, 2)

        self.generation_action_bar = GenerationActionBar(self.coordinator.queue_service)
        self.generation_action_bar.generate_requested.connect(self.prompt_panel.request_generation)
        generation_page_layout.addWidget(txt2img_content)
        generation_page_layout.addWidget(self.generation_action_bar)
        
        # Wire preview panel image drop events
        self.preview_panel.image_dropped.connect(self.handle_image_drop)
        # Gallery selection is local-only; context changes require the explicit load action.
        self.gallery_panel = GalleryPanel(self.coordinator)
        self.gallery_panel.context_load_requested.connect(self.on_gallery_context_load_requested)
        
        self.project_panel = ProjectPanel(self.coordinator)
        self.model_catalog_panel = ModelCatalogPanel(self.coordinator)
        self.queue_panel = QueuePanel(self.coordinator)
        self.settings_panel = SettingsPanel(self.coordinator)
        self.tips_panel = TipsPanel(self.coordinator)
        
        # Add Tabs
        self.tabs.addTab(txt2img_widget, "🎨 Generation")
        self.tabs.addTab(self.project_panel, "📁 Projects")
        self.gallery_tab_index = self.tabs.addTab(self.gallery_panel, "🖼️ Gallery")
        self.tabs.addTab(self.model_catalog_panel, "🤖 Model Catalog")
        self.tabs.addTab(self.queue_panel, "⏳ Job Queue")
        self.tabs.addTab(self.tips_panel, "💡 Tips")
        self.tabs.addTab(self.settings_panel, "⚙️ Settings")
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Gallery async warmup & grayout handlers
        self.gallery_panel.loading_started.connect(self.on_gallery_loading_started)
        self.gallery_panel.loading_finished.connect(self.on_gallery_loading_finished)
        QTimer.singleShot(50, self.gallery_panel.start_async_load)
        
        main_layout.addWidget(self.tabs)
        
        # Status Bar Panel at bottom
        self.status_panel = StatusPanel(self.coordinator)
        main_layout.addWidget(self.status_panel)

    def on_gallery_loading_started(self):
        if hasattr(self, 'gallery_tab_index'):
            self.tabs.setTabEnabled(self.gallery_tab_index, False)
            self.tabs.setTabText(self.gallery_tab_index, "🖼️ Gallery (読み込み中...)")

    def on_gallery_loading_finished(self):
        if hasattr(self, 'gallery_tab_index'):
            self.tabs.setTabEnabled(self.gallery_tab_index, True)
            self.tabs.setTabText(self.gallery_tab_index, "🖼️ Gallery")

    def on_tab_changed(self, index: int):
        widget = self.tabs.widget(index)
        if hasattr(widget, "ensure_initialized"):
            widget.ensure_initialized()

    def apply_theme(self, theme: str):
        dark_qss = """
        QMainWindow { background-color: #121212; }
        QTabWidget::pane { border: 1px solid #2c2c2e; background-color: #1e1e1e; border-radius: 6px; }
        QTabBar::tab { background-color: #2c2c2e; color: #8e8e93; padding: 8px 12px; border-radius: 4px; margin-right: 4px; }
        QTabBar::tab:selected { background-color: #0a84ff; color: white; font-weight: bold; }
        QPushButton { background-color: #2c2c2e; border: 1px solid #3a3a3c; border-radius: 4px; color: white; padding: 6px 12px; }
        QPushButton:hover { background-color: #3a3a3c; }
        QTextEdit, QLineEdit { background-color: #2c2c2e; border: 1px solid #3a3a3c; border-radius: 4px; color: white; }
        QComboBox { background-color: #2c2c2e; border: 1px solid #3a3a3c; border-radius: 4px; color: white; padding: 4px; }
        QComboBox QAbstractItemView { background-color: #1c1c1e; color: #ffffff; selection-background-color: #0a84ff; selection-color: #ffffff; border: 1px solid #3a3a3c; }
        QGroupBox { font-weight: bold; border: 1px solid #2c2c2e; border-radius: 6px; margin-top: 12px; color: #ffffff; }
        QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px 0 3px; }
        QTableWidget { background-color: #1e1e1e; gridline-color: #2c2c2e; color: #ffffff; }
        QHeaderView::section { background-color: #2c2c2e; color: #ffffff; border: 1px solid #3a3a3c; padding: 4px; }
        QTextBrowser { background-color: #1e1e1e; color: #f8fafc; border: 1px solid #2c2c2e; font-size: 13px; line-height: 1.6; }
        QWidget { font-family: "Segoe UI", "Yu Gothic UI", sans-serif; font-size: 13px; }
        """
        light_qss = """
        QMainWindow { background-color: #f2f2f7; }
        QTabWidget::pane { border: 1px solid #c7c7cc; background-color: #ffffff; border-radius: 6px; }
        QTabBar::tab { background-color: #e5e5ea; color: #555559; padding: 8px 12px; border-radius: 4px; margin-right: 4px; }
        QTabBar::tab:selected { background-color: #007aff; color: white; font-weight: bold; }
        QPushButton { background-color: #ffffff; border: 1px solid #c7c7cc; border-radius: 4px; color: #000000; padding: 6px 12px; }
        QPushButton:hover { background-color: #e5e5ea; }
        QTextEdit, QLineEdit { background-color: #ffffff; border: 1px solid #c7c7cc; border-radius: 4px; color: #000000; }
        QComboBox { background-color: #ffffff; border: 1px solid #c7c7cc; border-radius: 4px; color: #000000; padding: 4px; }
        QComboBox QAbstractItemView { background-color: #ffffff; color: #000000; selection-background-color: #007aff; selection-color: #ffffff; border: 1px solid #c7c7cc; }
        QGroupBox { font-weight: bold; border: 1px solid #c7c7cc; border-radius: 6px; margin-top: 12px; color: #000000; }
        QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px 0 3px; }
        QTableWidget { background-color: #ffffff; gridline-color: #e5e5ea; color: #000000; }
        QHeaderView::section { background-color: #f2f2f7; color: #000000; border: 1px solid #c7c7cc; padding: 4px; }
        QTextBrowser { background-color: #ffffff; color: #1c1c1e; border: 1px solid #c7c7cc; font-size: 13px; line-height: 1.6; }
        QWidget { font-family: "Segoe UI", "Yu Gothic UI", sans-serif; font-size: 13px; }
        """
        if theme == "Dark":
            self.setStyleSheet(dark_qss)
        elif theme == "Light":
            self.setStyleSheet(light_qss)
        else:
            self.setStyleSheet(dark_qss)

    @Slot(dict)
    def on_generation_requested(self, params: dict):
        # Insert job into persistent SQLite Job queue backlog
        active_project_id = self.coordinator.project_service.get_active_project_id()
        model_id = params.get("model_id")
        from api.model_registry import MODEL_REGISTRY
        model_meta = MODEL_REGISTRY.get(model_id) if isinstance(model_id, str) else None
        if not model_meta:
            QMessageBox.warning(
                self,
                "Model unavailable",
                "The selected model is no longer available. Please choose another model.",
            )
            return
        provider = model_meta["provider"]
        
        image_path = params.get("image_path")
        mask_path = params.get("mask_path")
        mode = "edit" if image_path else "generate"
        
        job_id = self.coordinator.queue_service.add_job(
            project_id=active_project_id,
            prompt_jp=params.get("prompt_jp", ""),
            translation_rule=params.get("translation_rule", "Standard"),

            size=params.get("size", "1024x1024"),
            negative_prompt=params.get("negative_prompt", ""),
            quality=params.get("quality", "standard"),
            batch_count=params.get("batch_count", 1),
            model_id=model_id,
            provider=provider,
            mode=mode,
            image_path=image_path,
            mask_path=mask_path,
            style_preset=params.get("style_preset"),
            expert_params=params.get("expert_params")
        )
        if job_id <= 0:
            QMessageBox.critical(
                self, "Queue error", "The generation job could not be saved to the queue."
            )
            return

        event_bus.status_updated.emit("Generation added to Background Job Queue successfully.")

    @Slot(dict)
    def on_image_generated(self, result: dict):
        if result.get("success"):
            image_path = result.get("image_path")
            if image_path:
                self.preview_panel.set_image(image_path, result)
                # Sync generation context
                self.coordinator.generation_service.set_context(
                    prompt_jp=result.get("prompt_jp", ""),
                    prompt_en=result.get("prompt_en", ""),

                    size=result.get("size", "1024x1024"),
                    negative_prompt=result.get("negative_prompt", "")
                )
                self.prompt_panel.update_context_label()

    @Slot(str, dict)
    def on_gallery_context_load_requested(self, image_path: str, metadata: dict):
        if image_path:
            self.preview_panel.set_image(image_path, metadata)
            self.coordinator.generation_service.set_context(
                prompt_jp=metadata.get("prompt_jp", ""),
                prompt_en=metadata.get("prompt_en", ""),
                size=metadata.get("size", "1024x1024"),
                negative_prompt=metadata.get("negative_prompt", "")
            )
            event_bus.context_changed.emit(metadata)
            self.prompt_panel.update_context_label()
            event_bus.status_updated.emit("Gallery prompt context loaded.")

    @Slot(str)
    def handle_image_drop(self, file_path: str):
        if not file_path:
            return
        import os
        metadata = {
            "image_path": file_path,
            "prompt_jp": "",
            "prompt_en": "",
            "negative_prompt": "",
            "style": "なし",
            "style_preset": "なし",
            "size": "1024x1024",
            "model_name": "Reference Image",
            "provider": "Local"
        }
        self.preview_panel.set_image(file_path, metadata)
        event_bus.status_updated.emit(f"参照画像を設定しました: {os.path.basename(file_path)}")

    @Slot(dict)
    def on_context_changed_generic(self, context: dict):
        if "switch_tab" in context:
            self.tabs.setCurrentIndex(context["switch_tab"])
        if context.get("clear_preview"):
            self.preview_panel.clear_preview()

    def closeEvent(self, event):
        if self._shutdown_complete:
            super().closeEvent(event)
            return

        if self.coordinator.shutdown(timeout_seconds=0.05):
            self._shutdown_complete = True
            super().closeEvent(event)
            return

        event.ignore()
        if not self._shutdown_pending:
            self._shutdown_pending = True
            self.setEnabled(False)
            event_bus.status_updated.emit(
                "Waiting for the active generation request to finish safely before closing..."
            )
            self._shutdown_timer.start()

    def _poll_shutdown(self):
        if not self.coordinator.shutdown(timeout_seconds=0.0):
            return
        self._shutdown_timer.stop()
        self._shutdown_complete = True
        self._shutdown_pending = False
        self.setEnabled(True)
        self.close()
