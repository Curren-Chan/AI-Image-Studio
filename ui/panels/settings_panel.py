# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QGroupBox, QGridLayout, QMessageBox,
    QScrollArea, QFrame
)
from core.event_bus import event_bus

class SettingsPanel(QWidget):
    def __init__(self, coordinator, parent=None):
        super().__init__(parent)
        self.coordinator = coordinator
        self.model_checkboxes = {}
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        # We wrap in a scroll area to prevent overflow on smaller screens
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(15)
        
        # 1. API Credentials Group
        api_group = QGroupBox("API Keys Settings")
        api_grid = QGridLayout(api_group)
        api_grid.setSpacing(10)
        
        # OpenAI Key
        api_grid.addWidget(QLabel("OpenAI API Key:"), 0, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("sk-proj-...")
        api_grid.addWidget(self.api_key_input, 0, 1)
        
        self.btn_save_api = QPushButton("💾 Update Key")
        self.btn_save_api.clicked.connect(self.save_api_key)
        api_grid.addWidget(self.btn_save_api, 0, 2)
        
        # fal.ai Key
        api_grid.addWidget(QLabel("fal.ai API Key (FAL_KEY):"), 1, 0)
        self.fal_key_input = QLineEdit()
        self.fal_key_input.setEchoMode(QLineEdit.Password)
        self.fal_key_input.setPlaceholderText("fal-...")
        api_grid.addWidget(self.fal_key_input, 1, 1)
        
        self.btn_save_fal = QPushButton("💾 Update Key")
        self.btn_save_fal.clicked.connect(self.save_fal_key)
        api_grid.addWidget(self.btn_save_fal, 1, 2)

        # Gemini Key
        api_grid.addWidget(QLabel("Gemini API Key (GEMINI_API_KEY):"), 2, 0)
        self.gemini_key_input = QLineEdit()
        self.gemini_key_input.setEchoMode(QLineEdit.Password)
        self.gemini_key_input.setPlaceholderText("AIzaSy...")
        api_grid.addWidget(self.gemini_key_input, 2, 1)
        
        self.btn_save_gemini = QPushButton("💾 Update Key")
        self.btn_save_gemini.clicked.connect(self.save_gemini_key)
        api_grid.addWidget(self.btn_save_gemini, 2, 2)

        # xAI Grok Key
        api_grid.addWidget(QLabel("Grok API Key (XAI_API_KEY):"), 3, 0)
        self.xai_key_input = QLineEdit()
        self.xai_key_input.setEchoMode(QLineEdit.Password)
        self.xai_key_input.setPlaceholderText("xai-...")
        api_grid.addWidget(self.xai_key_input, 3, 1)
        
        self.btn_save_xai = QPushButton("💾 Update Key")
        self.btn_save_xai.clicked.connect(self.save_xai_key)
        api_grid.addWidget(self.btn_save_xai, 3, 2)

        # HotAPI Key
        api_grid.addWidget(QLabel("HotAPI Key (HOTAPI_KEY):"), 4, 0)
        self.hotapi_key_input = QLineEdit()
        self.hotapi_key_input.setEchoMode(QLineEdit.Password)
        self.hotapi_key_input.setPlaceholderText("hk_live_...")
        api_grid.addWidget(self.hotapi_key_input, 4, 1)
        
        self.btn_save_hotapi = QPushButton("💾 Update Key")
        self.btn_save_hotapi.clicked.connect(self.save_hotapi_key)
        api_grid.addWidget(self.btn_save_hotapi, 4, 2)
        
        scroll_layout.addWidget(api_group)
        
        # 2. Translation engine selector Group
        translation_group = QGroupBox("Prompt Translation Model (翻訳エンジン)")
        translation_grid = QGridLayout(translation_group)
        translation_grid.setSpacing(10)
        
        translation_grid.addWidget(QLabel("Translation Engine:"), 0, 0)
        self.translation_menu = QComboBox()
        self.translation_menu.addItem("OpenAI GPT-4o-mini", "openai")
        self.translation_menu.addItem("gemini-3.1-flash-lite", "gemini")
        self.translation_menu.currentIndexChanged.connect(self.translation_provider_changed)
        translation_grid.addWidget(self.translation_menu, 0, 1)
        
        scroll_layout.addWidget(translation_group)

        # 3. Budget & Billing settings
        budget_group = QGroupBox("Budget & Balance Limits (概算使用料金)")
        budget_grid = QGridLayout(budget_group)
        budget_grid.setSpacing(10)
        
        # OpenAI
        budget_grid.addWidget(QLabel("Reset OpenAI balance ($):"), 0, 0)
        self.budget_openai_input = QLineEdit("10.00")
        budget_grid.addWidget(self.budget_openai_input, 0, 1)
        self.btn_reset_openai = QPushButton("🔄 Reset OpenAI Balance")
        self.btn_reset_openai.clicked.connect(self.reset_openai_balance)
        budget_grid.addWidget(self.btn_reset_openai, 0, 2)

        # fal.ai
        budget_grid.addWidget(QLabel("Reset fal.ai balance ($):"), 1, 0)
        self.budget_fal_input = QLineEdit("10.00")
        budget_grid.addWidget(self.budget_fal_input, 1, 1)
        self.btn_reset_fal = QPushButton("🔄 Reset fal.ai Balance")
        self.btn_reset_fal.clicked.connect(self.reset_fal_balance)
        budget_grid.addWidget(self.btn_reset_fal, 1, 2)

        # Grok
        budget_grid.addWidget(QLabel("Reset Grok balance ($):"), 2, 0)
        self.budget_grok_input = QLineEdit("10.00")
        budget_grid.addWidget(self.budget_grok_input, 2, 1)
        self.btn_reset_grok = QPushButton("🔄 Reset Grok Balance")
        self.btn_reset_grok.clicked.connect(self.reset_grok_balance)
        budget_grid.addWidget(self.btn_reset_grok, 2, 2)

        # HotAPI
        budget_grid.addWidget(QLabel("Reset HotAPI balance ($):"), 3, 0)
        self.budget_hotapi_input = QLineEdit("10.00")
        budget_grid.addWidget(self.budget_hotapi_input, 3, 1)
        self.btn_reset_hotapi = QPushButton("🔄 Reset HotAPI Balance")
        self.btn_reset_hotapi.clicked.connect(self.reset_hotapi_balance)
        budget_grid.addWidget(self.btn_reset_hotapi, 3, 2)

        scroll_layout.addWidget(budget_group)
        
        # 4. GUI Appearance Group
        gui_group = QGroupBox("GUI Appearance Settings")
        gui_grid = QGridLayout(gui_group)
        gui_grid.setSpacing(10)
        
        gui_grid.addWidget(QLabel("Theme Selector:"), 0, 0)
        self.theme_menu = QComboBox()
        self.theme_menu.addItems(["Dark", "Light", "Auto"])
        self.theme_menu.currentTextChanged.connect(self.theme_changed)
        gui_grid.addWidget(self.theme_menu, 0, 1)
        
        scroll_layout.addWidget(gui_group)
        scroll_layout.addStretch()
        
        main_scroll.setWidget(scroll_widget)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(main_scroll)

    def load_settings(self):
        # Load API keys
        self.api_key_input.setText(self.coordinator.settings_service.get_api_key())
        self.fal_key_input.setText(self.coordinator.settings_service.get_fal_key())
        self.gemini_key_input.setText(self.coordinator.settings_service.get_gemini_key())
        self.xai_key_input.setText(self.coordinator.settings_service.get_xai_key())
        self.hotapi_key_input.setText(self.coordinator.settings_service.get_hotapi_key())
        
        # Load budgets
        self.budget_openai_input.setText(str(self.coordinator.settings_service.get_setting("balance_openai", "10.00")))
        self.budget_fal_input.setText(str(self.coordinator.settings_service.get_setting("balance_fal", "10.00")))
        self.budget_grok_input.setText(str(self.coordinator.settings_service.get_setting("balance_grok", "10.00")))
        self.budget_hotapi_input.setText(str(self.coordinator.settings_service.get_setting("balance_hotapi", "10.00")))
        
        # Load theme
        theme = self.coordinator.settings_service.get_setting("theme", "Dark")
        self.theme_menu.setCurrentText(theme)
        
        # Load Translation provider selection
        provider = self.coordinator.settings_service.get_setting("translation_provider", "openai")
        idx = self.translation_menu.findData(provider)
        if idx != -1:
            self.translation_menu.setCurrentIndex(idx)

    def save_api_key(self):
        key = self.api_key_input.text().strip()
        self.coordinator.settings_service.update_api_key(key)
        self.coordinator.api_client.update_api_key(key)
        status = "OpenAI API Client successfully updated." if key else "OpenAI Client set to Mock Simulation Mode."
        event_bus.status_updated.emit(status)
        QMessageBox.information(self, "API Key Settings", "OpenAI API key updated successfully.")

    def save_fal_key(self):
        key = self.fal_key_input.text().strip()
        self.coordinator.settings_service.update_fal_key(key)
        self.coordinator.api_client.update_fal_key(key)
        status = "fal.ai API Client successfully updated." if key else "fal.ai Client set to Mock Simulation Mode."
        event_bus.status_updated.emit(status)
        QMessageBox.information(self, "API Key Settings", "fal.ai API key updated successfully.")

    def save_gemini_key(self):
        key = self.gemini_key_input.text().strip()
        self.coordinator.settings_service.update_gemini_key(key)
        self.coordinator.api_client.update_gemini_key(key)
        status = "Gemini API Client successfully updated." if key else "Gemini Client set to Mock Simulation Mode."
        event_bus.status_updated.emit(status)
        QMessageBox.information(self, "API Key Settings", "Gemini API key updated successfully.")

    def save_xai_key(self):
        key = self.xai_key_input.text().strip()
        self.coordinator.settings_service.update_xai_key(key)
        self.coordinator.api_client.update_xai_key(key)
        status = "Grok API Client successfully updated." if key else "Grok Client set to Mock Simulation Mode."
        event_bus.status_updated.emit(status)
        QMessageBox.information(self, "API Key Settings", "Grok API key updated successfully.")

    def save_hotapi_key(self):
        key = self.hotapi_key_input.text().strip()
        self.coordinator.settings_service.update_hotapi_key(key)
        self.coordinator.api_client.update_hotapi_key(key)
        status = "HotAPI Client successfully updated." if key else "HotAPI Client set to Mock Simulation Mode."
        event_bus.status_updated.emit(status)
        QMessageBox.information(self, "API Key Settings", "HotAPI key updated successfully.")

    def translation_provider_changed(self, index):
        provider = self.translation_menu.itemData(index)
        self.coordinator.settings_service.save_setting("translation_provider", provider)
        event_bus.status_updated.emit(f"Prompt translation provider changed to: {provider}")

    def reset_openai_balance(self):
        try:
            val = float(self.budget_openai_input.text().strip())
            self.coordinator.settings_service.save_setting("balance_openai", f"{val:.5f}")
            event_bus.preset_updated.emit()
            QMessageBox.information(self, "OpenAI Balance", f"OpenAI balance reset to: ${val:.5f}")
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid numeric value entered for OpenAI balance.")

    def reset_fal_balance(self):
        try:
            val = float(self.budget_fal_input.text().strip())
            self.coordinator.settings_service.save_setting("balance_fal", f"{val:.5f}")
            event_bus.preset_updated.emit()
            QMessageBox.information(self, "fal.ai Balance", f"fal.ai balance reset to: ${val:.5f}")
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid numeric value entered for fal.ai balance.")

    def reset_grok_balance(self):
        try:
            val = float(self.budget_grok_input.text().strip())
            self.coordinator.settings_service.save_setting("balance_grok", f"{val:.5f}")
            event_bus.preset_updated.emit()
            QMessageBox.information(self, "Grok Balance", f"Grok balance reset to: ${val:.5f}")
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid numeric value entered for Grok balance.")

    def reset_hotapi_balance(self):
        try:
            val = float(self.budget_hotapi_input.text().strip())
            self.coordinator.settings_service.save_setting("balance_hotapi", f"{val:.5f}")
            event_bus.preset_updated.emit()
            QMessageBox.information(self, "HotAPI Balance", f"HotAPI balance reset to: ${val:.5f}")
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid numeric value entered for HotAPI balance.")

    def theme_changed(self, text):
        self.coordinator.settings_service.save_setting("theme", text)
        event_bus.theme_changed.emit(text)
