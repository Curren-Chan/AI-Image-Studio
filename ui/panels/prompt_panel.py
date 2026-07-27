# -*- coding: utf-8 -*-
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QComboBox, QRadioButton, QSpinBox, QGroupBox, 
    QGridLayout, QFrame, QLineEdit, QMessageBox, QButtonGroup, QStackedWidget
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIntValidator
from core.event_bus import event_bus
from api.model_registry import MODEL_REGISTRY
from ui.dialogs.character_dialog import CharacterDialog
from ui.dialogs.product_dialog import ProductDialog
from services.translation.translation_rules import get_available_rules
from ui.panels.expert_model_panel import ExpertModelPanel

class PromptPanel(QWidget):
    def __init__(self, coordinator, parent=None):
        super().__init__(parent)
        self.coordinator = coordinator
        self.init_ui()
        self.load_presets()
        
        # Connect signals
        self.prompt_temp_menu.currentTextChanged.connect(self.on_prompt_template_changed)
        self.on_prompt_template_changed(self.prompt_temp_menu.currentText())
        
        self.neg_temp_menu.currentTextChanged.connect(self.on_neg_template_changed)
        self.on_neg_template_changed(self.neg_temp_menu.currentText())
        
        event_bus.template_updated.connect(self.load_presets)
        event_bus.context_changed.connect(self.on_context_changed)
        event_bus.model_config_changed.connect(self.update_model_menu)
        event_bus.project_changed.connect(lambda proj_id: self.update_project_display())
        
        self.update_project_display()
        self.update_model_menu()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Project Label (top)
        self.project_label = QLabel()
        self.project_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #007aff;")
        layout.addWidget(self.project_label)
        
        # 1. Prompt Area Layout (Prompt Input + Action Buttons side-by-side)
        prompt_area_frame = QFrame()
        prompt_area_layout = QHBoxLayout(prompt_area_frame)
        prompt_area_layout.setContentsMargins(0, 0, 0, 0)
        prompt_area_layout.setSpacing(15)
        
        # Left side of Prompt Area: Label and Input
        prompt_input_box = QFrame()
        prompt_input_box_layout = QVBoxLayout(prompt_input_box)
        prompt_input_box_layout.setContentsMargins(0, 0, 0, 0)
        prompt_input_box_layout.setSpacing(5)
        
        lbl_layout = QHBoxLayout()
        prompt_title = QLabel("Prompt (日本語のプロットや要望)")
        prompt_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        lbl_layout.addWidget(prompt_title)
        
        self.context_label = QLabel("[+] New Project")
        self.context_label.setStyleSheet("color: #34C759; font-weight: bold;")
        lbl_layout.addWidget(self.context_label, 0, Qt.AlignRight)
        prompt_input_box_layout.addLayout(lbl_layout)
        
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("プロットやシチュエーションを入力... (例: 水彩画風の街並み)")
        self.prompt_input.setFixedHeight(150)
        self.prompt_input.textChanged.connect(self.on_prompt_text_user_edited)
        prompt_input_box_layout.addWidget(self.prompt_input)
        
        # Dynamic Advice Banner (shown when context is loaded)
        self.advice_banner = QFrame()
        self.advice_banner.setStyleSheet(
            "QFrame { background: #1c2738; border: 1px solid #2b3e5a; border-radius: 6px; margin-top: 4px; }"
        )
        advice_layout = QHBoxLayout(self.advice_banner)
        advice_layout.setContentsMargins(8, 5, 8, 5)
        advice_layout.setSpacing(6)
        self.advice_label = QLabel()
        self.advice_label.setStyleSheet("color: #93c5fd; font-size: 12px; font-weight: 500;")
        advice_layout.addWidget(self.advice_label)
        self.advice_banner.setVisible(False)
        prompt_input_box_layout.addWidget(self.advice_banner)
        
        prompt_area_layout.addWidget(prompt_input_box, 4)
        
        # Right side of Prompt Area: Action Buttons
        actions_box = QFrame()
        actions_layout = QVBoxLayout(actions_box)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(6)
        
        self.new_proj_btn = QPushButton("New Create")
        self.new_proj_btn.setFixedHeight(40)
        self.new_proj_btn.setStyleSheet(
            "QPushButton { background-color: #34c759; color: white; font-weight: bold; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #30b350; }"
            "QPushButton:pressed { background-color: #248a3d; }"
            "QPushButton:disabled { background-color: #3a3a3c; color: #8e8e93; }"
        )
        self.new_proj_btn.clicked.connect(self.clear_generation_context)
        actions_layout.addWidget(self.new_proj_btn)
        
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setStyleSheet(
            "QPushButton { background-color: #5856d6; color: white; font-size: 14px; font-weight: bold; border-radius: 6px; border: none; }"
            "QPushButton:hover { background-color: #6e6cf0; }"
            "QPushButton:pressed { background-color: #403e9c; }"
            "QPushButton:disabled { background-color: #3a3a3c; color: #8e8e93; }"
        )
        self.generate_btn.setFixedHeight(75)
        self.generate_btn.clicked.connect(self.request_generation)
        actions_layout.addWidget(self.generate_btn)
        
        self.clear_context_btn = QPushButton("Clear Context")
        self.clear_context_btn.setFixedHeight(40)
        self.clear_context_btn.setStyleSheet(
            "QPushButton { background-color: transparent; border: 1px solid #ff453a; color: #ff453a; font-weight: bold; border-radius: 5px; }"
            "QPushButton:hover { background-color: #ff453a; color: white; }"
            "QPushButton:pressed { background-color: #d63629; color: white; }"
            "QPushButton:disabled { border-color: #3a3a3c; color: #8e8e93; }"
        )
        self.clear_context_btn.clicked.connect(self.clear_only_text)
        actions_layout.addWidget(self.clear_context_btn)
        
        prompt_area_layout.addWidget(actions_box, 1)
        layout.addWidget(prompt_area_frame)
        
        # 2. Negative Prompt Area (Spans full width, positioned below Prompt Area)
        neg_prompt_box = QFrame()
        neg_prompt_layout = QVBoxLayout(neg_prompt_box)
        neg_prompt_layout.setContentsMargins(0, 0, 0, 0)
        neg_prompt_layout.setSpacing(5)
        
        neg_title = QLabel("Negative Prompt (除外したい要素)")
        neg_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        neg_prompt_layout.addWidget(neg_title)
        
        self.neg_prompt_input = QTextEdit()
        self.neg_prompt_input.setPlaceholderText("除外したいキーワード... (例: text, low quality)")
        self.neg_prompt_input.setFixedHeight(60)
        neg_prompt_layout.addWidget(self.neg_prompt_input)
        
        layout.addWidget(neg_prompt_box)
        
        # 3. Generation Mode Selector Segmented Buttons
        mode_frame = QFrame()
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(0, 5, 0, 5)
        mode_layout.setSpacing(10)
        
        self.btn_gen_mode = QPushButton("🎨 生成モード (Text to Image)")
        self.btn_gen_mode.setCheckable(True)
        self.btn_gen_mode.setChecked(True)
        self.btn_gen_mode.setFixedHeight(35)
        
        self.btn_edit_mode = QPushButton("✏️ 編集モード (Image Editing)")
        self.btn_edit_mode.setCheckable(True)
        self.btn_edit_mode.setFixedHeight(35)
        
        self.btn_gen_mode.setStyleSheet(
            "QPushButton { background-color: #25324a; border: 1px solid #3a4a65; border-radius: 6px; color: #94a3b8; font-weight: bold; }"
            "QPushButton:checked { background-color: #007aff; border-color: #007aff; color: white; }"
        )
        self.btn_edit_mode.setStyleSheet(
            "QPushButton { background-color: #25324a; border: 1px solid #3a4a65; border-radius: 6px; color: #94a3b8; font-weight: bold; }"
            "QPushButton:checked { background-color: #ff9500; border-color: #ff9500; color: white; }"
        )
        
        self.btn_gen_mode.clicked.connect(lambda: self.set_generation_mode("generate"))
        self.btn_edit_mode.clicked.connect(lambda: self.set_generation_mode("edit"))
        
        mode_layout.addWidget(self.btn_gen_mode)
        mode_layout.addWidget(self.btn_edit_mode)
        layout.addWidget(mode_frame)
        
        # Generation Parameters Settings Group Box
        gen_group = QGroupBox("Generation Parameters")
        gen_grid = QGridLayout(gen_group)
        gen_grid.setSpacing(10)
        gen_grid.setColumnStretch(0, 0)
        gen_grid.setColumnStretch(1, 3)
        gen_grid.setColumnStretch(2, 2)
        gen_grid.setColumnStretch(3, 2)
        
        # Row 0: Active Model Selection
        self.lbl_ai_model = QLabel("AI Model:")
        gen_grid.addWidget(self.lbl_ai_model, 0, 0)
        self.model_menu = QComboBox()
        self.model_menu.setFixedHeight(30)
        self.model_menu.currentIndexChanged.connect(self.on_model_changed)
        gen_grid.addWidget(self.model_menu, 0, 1, 1, 3)
        
        # Expert Parameters Area (unified stacked container, no tab bar)
        self.expert_stack_widget = QStackedWidget()
        self.expert_stack_widget.setVisible(True)
        self.expert_stack_widget.setMinimumHeight(150)
        gen_grid.addWidget(self.expert_stack_widget, 1, 0, 1, 4)
        
        # Row 2: Translation Rule
        gen_grid.addWidget(QLabel("Translation Rule:"), 2, 0)
        
        self.rule_container = QWidget()
        rule_layout = QHBoxLayout(self.rule_container)
        rule_layout.setContentsMargins(0, 0, 0, 0)
        rule_layout.setSpacing(10)
        
        self.rule_group = QButtonGroup(self)
        available_rules = get_available_rules()
        
        for idx, rule_name in enumerate(available_rules):
            btn = QRadioButton(rule_name)
            if rule_name == "Standard" or idx == 0:
                btn.setChecked(True)
            self.rule_group.addButton(btn)
            rule_layout.addWidget(btn)
            
        rule_layout.addStretch()
        gen_grid.addWidget(self.rule_container, 2, 1, 1, 3)
        
        # Row 3: Style Preset
        gen_grid.addWidget(QLabel("Style Preset:"), 3, 0)
        self.style_preset_menu = QComboBox()
        self.style_preset_menu.setFixedHeight(30)
        gen_grid.addWidget(self.style_preset_menu, 3, 1)
        
        self.style_preset_manager_btn = QPushButton("⚙️ Manage Presets")
        self.style_preset_manager_btn.setFixedHeight(30)
        self.style_preset_manager_btn.clicked.connect(self.open_style_preset_manager)
        gen_grid.addWidget(self.style_preset_manager_btn, 3, 2, 1, 2)

        # Row 4: Prompt Template
        gen_grid.addWidget(QLabel("Prompt Template:"), 4, 0)
        self.prompt_temp_menu = QComboBox()
        self.prompt_temp_menu.setFixedHeight(30)
        gen_grid.addWidget(self.prompt_temp_menu, 4, 1)
        
        self.prompt_temp_insert_btn = QPushButton("✍️ Insert to Prompt")
        self.prompt_temp_insert_btn.setFixedHeight(30)
        self.prompt_temp_insert_btn.setStyleSheet(
            "QPushButton { background-color: #007aff; color: white; font-weight: bold; border-radius: 4px; border: none; }"
            "QPushButton:hover { background-color: #148cff; }"
            "QPushButton:pressed { background-color: #0062c4; }"
            "QPushButton:disabled { background-color: #3a3a3c; color: #8e8e93; }"
        )
        self.prompt_temp_insert_btn.clicked.connect(self.insert_prompt_template_to_prompt)
        gen_grid.addWidget(self.prompt_temp_insert_btn, 4, 2)
        
        self.prompt_temp_manager_btn = QPushButton("⚙️ Manage Templates")
        self.prompt_temp_manager_btn.setFixedHeight(30)
        self.prompt_temp_manager_btn.clicked.connect(self.open_prompt_template_manager)
        gen_grid.addWidget(self.prompt_temp_manager_btn, 4, 3)
 
        # Row 5: Negative Template
        gen_grid.addWidget(QLabel("Negative Template:"), 5, 0)
        self.neg_temp_menu = QComboBox()
        self.neg_temp_menu.setFixedHeight(30)
        gen_grid.addWidget(self.neg_temp_menu, 5, 1)
        
        self.neg_temp_insert_btn = QPushButton("✍️ Insert to Negative")
        self.neg_temp_insert_btn.setFixedHeight(30)
        self.neg_temp_insert_btn.setStyleSheet(
            "QPushButton { background-color: #007aff; color: white; font-weight: bold; border-radius: 4px; border: none; }"
            "QPushButton:hover { background-color: #148cff; }"
            "QPushButton:pressed { background-color: #0062c4; }"
            "QPushButton:disabled { background-color: #3a3a3c; color: #8e8e93; }"
        )
        self.neg_temp_insert_btn.clicked.connect(self.insert_neg_template_to_neg_prompt)
        gen_grid.addWidget(self.neg_temp_insert_btn, 5, 2)
        
        self.neg_temp_manager_btn = QPushButton("⚙️ Manage Templates")
        self.neg_temp_manager_btn.setFixedHeight(30)
        self.neg_temp_manager_btn.clicked.connect(self.open_neg_template_manager)
        gen_grid.addWidget(self.neg_temp_manager_btn, 5, 3)
        
        # Row 6: Size Aspect Ratio
        gen_grid.addWidget(QLabel("Size Aspect Ratio:"), 6, 0)
        self.size_menu = QComboBox()
        self.size_menu.setFixedHeight(30)
        self.size_menu.currentTextChanged.connect(self.on_size_preset_changed)
        gen_grid.addWidget(self.size_menu, 6, 1, 1, 3)
        
        # Row 7: Custom Dimensions inputs
        self.custom_size_box = QFrame()
        custom_size_layout = QHBoxLayout(self.custom_size_box)
        custom_size_layout.setContentsMargins(0, 0, 0, 0)
        custom_size_layout.addWidget(QLabel("W:"))
        self.width_input = QLineEdit("1024")
        self.width_input.setValidator(QIntValidator(64, 4096, self.width_input))
        self.width_input.setFixedHeight(30)
        custom_size_layout.addWidget(self.width_input)
        custom_size_layout.addWidget(QLabel("H:"))
        self.height_input = QLineEdit("1024")
        self.height_input.setValidator(QIntValidator(64, 4096, self.height_input))
        self.height_input.setFixedHeight(30)
        custom_size_layout.addWidget(self.height_input)
        gen_grid.addWidget(self.custom_size_box, 7, 1, 1, 3)
        self.custom_size_box.setVisible(False)
        
        # Row 8: Quality Radio Buttons
        self.lbl_quality = QLabel("Quality (OpenAI):")
        gen_grid.addWidget(self.lbl_quality, 8, 0)
        self.quality_frame = QFrame()
        quality_layout = QHBoxLayout(self.quality_frame)
        quality_layout.setContentsMargins(0, 0, 0, 0)
        quality_layout.setSpacing(10)
        self.quality_standard = QRadioButton("Standard")
        self.quality_hd = QRadioButton("High Quality")
        self.quality_standard.setChecked(True)
        quality_layout.addWidget(self.quality_standard)
        quality_layout.addWidget(self.quality_hd)
        gen_grid.addWidget(self.quality_frame, 8, 1, 1, 3)
  
        # Row 9: Batch Count Spinbox
        gen_grid.addWidget(QLabel("Batch Count (枚数):"), 9, 0)
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 10)
        self.batch_spin.setValue(1)
        self.batch_spin.setFixedHeight(30)
        gen_grid.addWidget(self.batch_spin, 9, 1, 1, 3)
        
        layout.addWidget(gen_group)
        
        # Prompt Helper Libraries (Compact layout)
        lib_group = QGroupBox("Prompt Helper Libraries")
        lib_layout = QHBoxLayout(lib_group)
        lib_layout.setContentsMargins(10, 10, 10, 10)
        lib_layout.setSpacing(10)
        
        self.char_lib_btn = QPushButton("👥 Character Library (キャラクター)")
        self.char_lib_btn.setFixedHeight(35)
        self.char_lib_btn.setStyleSheet(
            "QPushButton { background-color: transparent; border: 1px solid #007aff; color: #007aff; font-weight: bold; border-radius: 5px; }"
            "QPushButton:hover { background-color: #007aff; color: white; }"
            "QPushButton:pressed { background-color: #0056b3; color: white; }"
        )
        self.char_lib_btn.clicked.connect(self.open_character_library)
        lib_layout.addWidget(self.char_lib_btn)
        
        self.prod_lib_btn = QPushButton("📦 Product Library (プロダクト)")
        self.prod_lib_btn.setFixedHeight(35)
        self.prod_lib_btn.setStyleSheet(
            "QPushButton { background-color: transparent; border: 1px solid #ff9500; color: #ff9500; font-weight: bold; border-radius: 5px; }"
            "QPushButton:hover { background-color: #ff9500; color: white; }"
            "QPushButton:pressed { background-color: #cc7600; color: white; }"
        )
        self.prod_lib_btn.clicked.connect(self.open_product_library)
        lib_layout.addWidget(self.prod_lib_btn)
        
        layout.addWidget(lib_group)

    def load_presets(self):
        if hasattr(self, 'prompt_temp_menu'):
            current_prompt_temp = self.prompt_temp_menu.currentText()
            self.prompt_temp_menu.clear()
            prompt_templates = self.coordinator.template_service.get_prompt_templates()
            self.prompt_temp_menu.addItem("テンプレート無し")
            self.prompt_temp_menu.addItems(list(prompt_templates.keys()))
            if current_prompt_temp:
                self.prompt_temp_menu.setCurrentText(current_prompt_temp)
            self.on_prompt_template_changed(self.prompt_temp_menu.currentText())
            
        if hasattr(self, 'neg_temp_menu'):
            current_neg_temp = self.neg_temp_menu.currentText()
            self.neg_temp_menu.clear()
            neg_templates = self.coordinator.template_service.get_negative_templates()
            self.neg_temp_menu.addItem("テンプレート無し")
            self.neg_temp_menu.addItems(list(neg_templates.keys()))
            if current_neg_temp:
                self.neg_temp_menu.setCurrentText(current_neg_temp)
            self.on_neg_template_changed(self.neg_temp_menu.currentText())

        if hasattr(self, 'style_preset_menu'):
            current_style_preset = self.style_preset_menu.currentText()
            self.style_preset_menu.clear()
            style_presets = self.coordinator.template_service.get_style_presets()
            self.style_preset_menu.addItem("プリセット無し")
            self.style_preset_menu.addItems(list(style_presets.keys()))
            if current_style_preset:
                self.style_preset_menu.setCurrentText(current_style_preset)

        # Keep models updated if settings changed
        self.update_model_menu()

    def set_generation_mode(self, mode: str):
        if mode == "generate":
            self.btn_gen_mode.setChecked(True)
            self.btn_edit_mode.setChecked(False)
        else:
            self.btn_gen_mode.setChecked(False)
            self.btn_edit_mode.setChecked(True)
            
        self.update_model_menu()
        self.update_context_label()

    def open_style_preset_manager(self):
        from ui.dialogs.template_dialog import TemplateDialog
        dialog = TemplateDialog(self.coordinator.template_service, active_tab_name="style_preset", parent=self)
        dialog.exec()

    def update_model_menu(self):
        if not hasattr(self, 'model_menu'):
            return
            
        current_model_id = self.model_menu.currentData()
            
        self.model_menu.blockSignals(True)
        self.expert_stack_widget.blockSignals(True)
        
        self.model_menu.clear()
        # Clear stack widget
        while self.expert_stack_widget.count() > 0:
            w = self.expert_stack_widget.widget(0)
            self.expert_stack_widget.removeWidget(w)
            w.deleteLater()
        
        # Get enabled models from settings
        enabled_str = self.coordinator.settings_service.get_setting("enabled_models", "")
        if not enabled_str:
            enabled_str = self.coordinator.settings_service.defaults["enabled_models"]
            
        enabled_ids = [x.strip() for x in enabled_str.split(",") if x.strip()]
        
        current_mode = "generate" if self.btn_gen_mode.isChecked() else "edit"
        
        for model_id in enabled_ids:
            model_meta = MODEL_REGISTRY.get(model_id)
            if not model_meta:
                continue
                
            # Filter based on compatibility
            cat = model_meta["category"]
            if current_mode == "generate" and cat == "img_edit":
                continue
            if current_mode == "edit" and cat == "text2img":
                continue
                
            self.model_menu.addItem(model_meta["display_name"], model_id)
            
            # Add to expert stack
            expert_panel = ExpertModelPanel(model_id, model_meta)
            expert_panel.setProperty("model_id", model_id)
            self.expert_stack_widget.addWidget(expert_panel)

        if self.model_menu.count() == 0:
            self.model_menu.addItem("No compatible enabled models", None)
            self.model_menu.setEnabled(False)
            self.size_menu.clear()
            self.custom_size_box.setVisible(False)
        else:
            self.model_menu.setEnabled(True)
            
        if current_model_id:
            idx = self.model_menu.findData(current_model_id)
            if idx >= 0:
                self.model_menu.setCurrentIndex(idx)
                
        self.model_menu.blockSignals(False)
        self.expert_stack_widget.blockSignals(False)
        self.on_model_changed()

    def on_model_changed(self):
        model_id = self.model_menu.currentData()
        if not model_id:
            self.quality_frame.setEnabled(False)
            self.neg_prompt_input.setEnabled(False)
            return
            
        model_meta = MODEL_REGISTRY.get(model_id)
        if not model_meta:
            return
            
        # Sync expert stacked container to match model selection
        if hasattr(self, 'expert_stack_widget'):
            for i in range(self.expert_stack_widget.count()):
                widget = self.expert_stack_widget.widget(i)
                if widget.property("model_id") == model_id:
                    self.expert_stack_widget.setCurrentWidget(widget)
                    break
            
        # Update size menu presets
        self.size_menu.blockSignals(True)
        self.size_menu.clear()
        
        for size_info in model_meta["sizes"]:
            self.size_menu.addItem(size_info["label"], size_info["value"])
            
        # Custom dimensions are validated again by GenerationService before any
        # provider or mock image allocation.
        self.size_menu.addItem("Custom...", "Custom...")
        self.size_menu.blockSignals(False)
        
        # Trigger aspect ratio change layout logic
        self.on_size_preset_changed(self.size_menu.currentText())
        
        # Support negative prompts or not
        supports_neg = model_meta.get("supports_negative_prompt", False)
        self.neg_prompt_input.setEnabled(supports_neg)
        if not supports_neg:
            self.neg_prompt_input.setPlaceholderText("選択されたモデルはネガティブプロンプトをサポートしていません")
            self.neg_prompt_input.clear()
        else:
            self.neg_prompt_input.setPlaceholderText("除外したいキーワード... (例: text, low quality)")
            
        # Enable quality selection only for OpenAI provider
        is_openai = model_meta.get("provider") == "openai"
        self.quality_frame.setEnabled(is_openai)
        if hasattr(self, 'lbl_quality'):
            self.lbl_quality.setEnabled(is_openai)


    def on_size_preset_changed(self, text):
        self.custom_size_box.setVisible("Custom..." in text)

    def append_tag(self, value):
        current_text = self.prompt_input.toPlainText().strip()
        if current_text:
            self.prompt_input.setPlainText(f"{current_text}, {value}")
        else:
            self.prompt_input.setPlainText(value)

    def get_selected_quality(self) -> str:
        if self.quality_hd.isChecked():
            return "hd"
        return "standard"

    def request_generation(self):
        self.hide_advice_banner()
        prompt_jp = self.prompt_input.toPlainText().strip()
        if not prompt_jp:
            return
            
        size_selection = self.size_menu.currentData()
        neg_prompt = self.neg_prompt_input.toPlainText().strip()
        quality = self.get_selected_quality()
        batch_count = self.batch_spin.value()
        model_id = self.model_menu.currentData()

        if not model_id or model_id not in MODEL_REGISTRY:
            QMessageBox.warning(
                self,
                "モデル未選択",
                "現在の生成モードに対応する有効なモデルがありません。モデルカタログでモデルを有効化してください。",
            )
            return
        
        # Parse custom size
        if size_selection == "Custom...":
            w = self.width_input.text().strip()
            h = self.height_input.text().strip()
            if not w or not h:
                QMessageBox.warning(self, "Invalid size", "幅と高さを入力してください。")
                return
            size = f"{w}x{h}"
        else:
            size = size_selection

        from services.generation_service import GenerationService

        valid_size, size_error = GenerationService.validate_size(size)
        if not valid_size:
            QMessageBox.warning(self, "Invalid size", size_error or "Invalid image size.")
            return
            
        is_edit = self.btn_edit_mode.isChecked()
        image_path = None
        
        if is_edit:
            main_win = self.window()
            if hasattr(main_win, "preview_panel") and main_win.preview_panel:
                image_path = main_win.preview_panel.current_image_path
                
            if not image_path or not os.path.isfile(image_path):
                QMessageBox.warning(self, "画像が見つかりません", "編集モードにはソース画像が必要です。プレビューエリアに画像をドラッグ＆ドロップするか、ギャラリーから画像を選択してください。")
                return
            
        expert_params = None
        target_widget = None
        if hasattr(self, "expert_stack_widget") and self.expert_stack_widget.count() > 0:
            target_widget = self.expert_stack_widget.currentWidget()
        if target_widget and hasattr(target_widget, "get_expert_params_json"):
            expert_params = target_widget.get_expert_params_json()
            
        # Emit generation event (handled by MainWindow or Coordinator)
        event_bus.generation_requested.emit({
            "prompt_jp": prompt_jp,
            "translation_rule": self.rule_group.checkedButton().text() if self.rule_group.checkedButton() else "Standard",
            "style": "",
            "style_preset": self.style_preset_menu.currentText(),
            "size": size,
            "negative_prompt": neg_prompt,
            "quality": quality,
            "batch_count": batch_count,
            "model_id": model_id,
            "image_path": image_path,
            "mask_path": None,
            "expert_params": expert_params
        })

    def show_advice_banner(self, is_edit: bool = False):
        if is_edit:
            msg = "✏️ ヒント: ソース画像とプロンプトがセットされました。変更したい部分や指示を書き足して生成してください。"
        else:
            msg = "💡 ヒント: プロンプトが読み込まれました。必要に応じて内容の修正や指示を追記して生成してください。"
        if hasattr(self, "advice_label") and hasattr(self, "advice_banner"):
            self.advice_label.setText(msg)
            self.advice_banner.setVisible(True)

    def hide_advice_banner(self):
        if hasattr(self, "advice_banner"):
            self.advice_banner.setVisible(False)

    def on_prompt_text_user_edited(self):
        if hasattr(self, "advice_banner") and self.advice_banner.isVisible():
            self.hide_advice_banner()

    def clear_generation_context(self):
        self.hide_advice_banner()
        self.coordinator.generation_service.new_project()
        self.prompt_input.clear()
        self.neg_prompt_input.clear()
        self.update_context_label()
        event_bus.context_changed.emit({"clear_preview": True})
        event_bus.status_updated.emit("Context cleared.")

    def clear_only_text(self):
        self.hide_advice_banner()
        self.prompt_input.clear()
        self.neg_prompt_input.clear()
        event_bus.status_updated.emit("Prompt text cleared.")

    def update_context_label(self):
        is_edit = hasattr(self, "btn_edit_mode") and self.btn_edit_mode.isChecked()
        
        if is_edit:
            main_win = self.window()
            image_path = None
            if hasattr(main_win, "preview_panel") and main_win.preview_panel:
                image_path = main_win.preview_panel.current_image_path
                
            if not image_path:
                self.context_label.setText("[⚠️] ソース画像を指定してください")
                self.context_label.setStyleSheet("color: #FF9500; font-weight: bold;")
            else:
                self.context_label.setText("[✏️] 編集モード (ソース画像あり)")
                self.context_label.setStyleSheet("color: #007AFF; font-weight: bold;")
            return

        if self.coordinator.generation_service.session_history:
            prev = self.coordinator.generation_service.session_history[-1]
            if prev.get("prompt_jp", "").startswith("[Dropped Image:"):
                self.context_label.setText("[🖼️] Dropped Image Context")
                self.context_label.setStyleSheet("color: #007AFF; font-weight: bold;")
            else:
                self.context_label.setText("[✏️] Modifying Context")
                self.context_label.setStyleSheet("color: #FF9500; font-weight: bold;")
        else:
            self.context_label.setText("[+] New Project")
            self.context_label.setStyleSheet("color: #34C759; font-weight: bold;")

    @Slot(dict)
    def on_context_changed(self, context):
        if "append_prompt" in context:
            self.append_tag(context["append_prompt"])
        else:
            self.prompt_input.blockSignals(True)
            self.prompt_input.setPlainText(context.get("prompt_jp", ""))
            self.prompt_input.blockSignals(False)
            self.neg_prompt_input.setPlainText(context.get("negative_prompt", ""))
            
            # Select size
            size = context.get("size", "1024x1024")
            found = False
            for i in range(self.size_menu.count()):
                if size == self.size_menu.itemData(i) or size in self.size_menu.itemText(i):
                    self.size_menu.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self.size_menu.setCurrentText("Custom...")
                try:
                    w, h = size.split("x")
                    self.width_input.setText(w)
                    self.height_input.setText(h)
                except Exception:
                    pass
            
            # Quality
            q = context.get("quality", "standard")
            if q in ("High", "hd"):
                self.quality_hd.setChecked(True)
            else:
                self.quality_standard.setChecked(True)
                
            # Style Engine
            if "translation_rule" in context:
                for btn in self.rule_group.buttons():
                    if btn.text() == context["translation_rule"]:
                        btn.setChecked(True)
                        break
            elif "style_engine" in context:
                for btn in self.rule_group.buttons():
                    if btn.text() == context["style_engine"]:
                        btn.setChecked(True)
                        break
            else:
                for btn in self.rule_group.buttons():
                    if btn.text() == "Standard":
                        btn.setChecked(True)
                        break
            
            # Style Preset
            if "style_preset" in context:
                self.style_preset_menu.setCurrentText(context["style_preset"])
            else:
                self.style_preset_menu.setCurrentText("プリセット無し")
                
            # Model Selection
            if "model_id" in context:
                model_id = context["model_id"]
                idx = self.model_menu.findData(model_id)
                if idx >= 0:
                    self.model_menu.setCurrentIndex(idx)
            
            # Expert parameters
            if "expert_params" in context:
                expert_params = context["expert_params"]
                if expert_params and hasattr(self, "expert_stack_widget"):
                    widget = self.expert_stack_widget.currentWidget()
                    if widget and hasattr(widget, "set_expert_params"):
                        widget.set_expert_params(expert_params)
            
            # If the context is changed via dragging image, we should probably toggle edit mode
            if context.get("image_path"):
                self.set_generation_mode("edit")
            else:
                self.update_context_label()

            # Trigger advice banner for user guidance
            is_edit_active = hasattr(self, "btn_edit_mode") and self.btn_edit_mode.isChecked()
            self.show_advice_banner(is_edit=is_edit_active)

    def open_character_library(self):
        dlg = CharacterDialog(self.coordinator.library_service, self)
        dlg.exec()
        
    def open_product_library(self):
        dlg = ProductDialog(self.coordinator.library_service, self)
        dlg.exec()

    def update_project_display(self):
        active_name = self.coordinator.project_service.get_active_project_name()
        self.project_label.setText(f"Project: {active_name}")

    def on_prompt_template_changed(self, text):
        if hasattr(self, 'prompt_temp_insert_btn'):
            self.prompt_temp_insert_btn.setEnabled(text != "テンプレート無し" and text != "")

    def on_neg_template_changed(self, text):
        if hasattr(self, 'neg_temp_insert_btn'):
            self.neg_temp_insert_btn.setEnabled(text != "テンプレート無し" and text != "")

    def insert_prompt_template_to_prompt(self):
        title = self.prompt_temp_menu.currentText()
        if not title or title == "テンプレート無し":
            return
        templates = self.coordinator.template_service.get_prompt_templates()
        content = templates.get(title, "")
        if content:
            self.append_tag(content)
            event_bus.status_updated.emit(f"Prompt template '{title}' inserted to prompt.")

    def insert_neg_template_to_neg_prompt(self):
        title = self.neg_temp_menu.currentText()
        if not title or title == "テンプレート無し":
            return
        templates = self.coordinator.template_service.get_negative_templates()
        content = templates.get(title, "")
        if content:
            self.append_neg_tag(content)
            event_bus.status_updated.emit(f"Negative template '{title}' inserted to negative prompt.")

    def append_neg_tag(self, value):
        current_text = self.neg_prompt_input.toPlainText().strip()
        if current_text:
            self.neg_prompt_input.setPlainText(f"{current_text}, {value}")
        else:
            self.neg_prompt_input.setPlainText(value)

    def open_prompt_template_manager(self):
        from ui.dialogs.template_dialog import TemplateDialog
        dlg = TemplateDialog(self.coordinator.template_service, active_tab_name="positive", parent=self)
        dlg.exec()

    def open_neg_template_manager(self):
        from ui.dialogs.template_dialog import TemplateDialog
        dlg = TemplateDialog(self.coordinator.template_service, active_tab_name="negative", parent=self)
        dlg.exec()
