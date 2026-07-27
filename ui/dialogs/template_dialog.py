from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit, 
    QTextEdit, QPushButton, QLabel, QMessageBox, QTabWidget, QGridLayout, QWidget
)
from core.event_bus import event_bus

class TemplateDialog(QDialog):
    def __init__(self, template_service, active_tab_name="positive", parent=None):
        super().__init__(parent)
        self.template_service = template_service
        self.setWindowTitle("Templates Manager (テンプレート管理)")
        self.resize(650, 450)
        self.selected_template_name = None
        self.active_type = active_tab_name # "positive", "negative", or "style_preset"
        
        self.init_ui()
        
        # Set active tab
        if self.active_type == "negative":
            self.tabs.setCurrentIndex(1)
        elif self.active_type == "style_preset":
            self.tabs.setCurrentIndex(2)
        else:
            self.tabs.setCurrentIndex(0)
            
        self.refresh_list()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Tabs to separate positive, negative and style templates
        self.tabs = QTabWidget()
        self.pos_tab = QWidget()
        self.neg_tab = QWidget()
        self.style_tab = QWidget()
        self.tabs.addTab(self.pos_tab, "Prompt Templates (プロンプト用)")
        self.tabs.addTab(self.neg_tab, "Negative Templates (除外要素用)")
        self.tabs.addTab(self.style_tab, "Style Presets (スタイル用)")
        layout.addWidget(self.tabs)
        
        # Main form below tabs (shared)
        main_layout = QHBoxLayout()
        
        # Left Panel: List
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Saved Templates:"))
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.list_widget)
        
        self.btn_new = QPushButton("New Template")
        self.btn_new.clicked.connect(self.clear_fields)
        left_layout.addWidget(self.btn_new)
        main_layout.addLayout(left_layout, 2)
        
        # Right Panel: Form
        form_layout = QVBoxLayout()
        form_layout.addWidget(QLabel("Template Details:"))
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Template Title:"), 0, 0)
        self.title_input = QLineEdit()
        grid.addWidget(self.title_input, 0, 1)
        
        grid.addWidget(QLabel("Content Text:"), 1, 0)
        self.content_input = QTextEdit()
        grid.addWidget(self.content_input, 1, 1)
        form_layout.addLayout(grid)
        
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save / Update")
        self.btn_save.clicked.connect(self.save_template)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_template)
        btn_layout.addWidget(self.btn_delete)
        
        form_layout.addLayout(btn_layout)
        form_layout.addStretch()
        main_layout.addLayout(form_layout, 3)
        
        layout.addLayout(main_layout)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
    def on_tab_changed(self, index):
        if index == 0:
            self.active_type = "positive"
        elif index == 1:
            self.active_type = "negative"
        else:
            self.active_type = "style_preset"
        self.clear_fields()
        self.refresh_list()
        
    def get_active_templates_dict(self) -> dict:
        if self.active_type == "positive":
            return self.template_service.get_prompt_templates()
        elif self.active_type == "negative":
            return self.template_service.get_negative_templates()
        else:
            return self.template_service.get_style_presets()
        
    def save_templates_dict(self, data: dict) -> bool:
        if self.active_type == "positive":
            return self.template_service.save_prompt_templates(data)
        elif self.active_type == "negative":
            return self.template_service.save_negative_templates(data)
        else:
            return self.template_service.save_style_presets(data)
            
    def refresh_list(self):
        self.list_widget.clear()
        self.templates = self.get_active_templates_dict()
        self.template_names = list(self.templates.keys())
        for name in self.template_names:
            self.list_widget.addItem(name)
            
    def on_selection_changed(self, index):
        if index < 0 or index >= len(self.template_names):
            return
        name = self.template_names[index]
        self.selected_template_name = name
        self.title_input.setText(name)
        self.content_input.setPlainText(self.templates[name])
        
    def clear_fields(self):
        self.selected_template_name = None
        self.title_input.clear()
        self.content_input.clear()
        self.list_widget.clearSelection()
        
    def save_template(self):
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        
        if not title or not content:
            QMessageBox.warning(self, "Validation Error", "Title and content cannot be empty.")
            return
            
        data = self.get_active_templates_dict().copy()
        
        if self.selected_template_name and self.selected_template_name != title:
            if self.selected_template_name in data:
                del data[self.selected_template_name]
                
        data[title] = content
        if not self.save_templates_dict(data):
            QMessageBox.critical(
                self,
                "Save Error",
                "The template could not be saved. Your current entries were left unchanged.",
            )
            return
        self.refresh_list()
        self.clear_fields()
        event_bus.template_updated.emit()
        QMessageBox.information(self, "Success", "Template saved successfully.")
        
    def delete_template(self):
        if not self.selected_template_name:
            return
        data = self.get_active_templates_dict().copy()
        if self.selected_template_name in data:
            del data[self.selected_template_name]
        if not self.save_templates_dict(data):
            QMessageBox.critical(
                self,
                "Delete Error",
                "The template could not be deleted. Please try again.",
            )
            return
        self.refresh_list()
        self.clear_fields()
        event_bus.template_updated.emit()
        QMessageBox.information(self, "Deleted", "Template deleted successfully.")
