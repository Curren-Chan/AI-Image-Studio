from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox, QGridLayout
from core.event_bus import event_bus

class CharacterDialog(QDialog):
    def __init__(self, library_service, parent=None):
        super().__init__(parent)
        self.library_service = library_service
        self.setWindowTitle("Character Library (キャラクター管理)")
        self.resize(600, 420)
        self.selected_character_id = None
        self.init_ui()
        self.refresh_list()
        
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Left Panel: List
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Characters List:"))
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.list_widget)
        
        self.btn_new = QPushButton("New Character")
        self.btn_new.clicked.connect(self.clear_fields)
        left_layout.addWidget(self.btn_new)
        main_layout.addLayout(left_layout, 2)
        
        # Right Panel: Form
        form_layout = QVBoxLayout()
        form_layout.addWidget(QLabel("Character Details:"))
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Name:"), 0, 0)
        self.name_input = QLineEdit()
        grid.addWidget(self.name_input, 0, 1)
        
        grid.addWidget(QLabel("Prompt fragment:"), 1, 0)
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("e.g. A young woman with blue hair, round glasses, and a gray scarf")
        grid.addWidget(self.prompt_input, 1, 1)
        
        grid.addWidget(QLabel("Description:"), 2, 0)
        self.desc_input = QLineEdit()
        grid.addWidget(self.desc_input, 2, 1)
        
        grid.addWidget(QLabel("Tags (comma sep):"), 3, 0)
        self.tags_input = QLineEdit()
        grid.addWidget(self.tags_input, 3, 1)
        
        form_layout.addLayout(grid)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save / Update")
        self.btn_save.clicked.connect(self.save_character)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_character)
        btn_layout.addWidget(self.btn_delete)
        
        self.btn_insert = QPushButton("Insert into Prompt")
        self.btn_insert.clicked.connect(self.insert_prompt)
        self.btn_insert.setStyleSheet("background-color: #007aff; color: white;")
        btn_layout.addWidget(self.btn_insert)
        
        form_layout.addLayout(btn_layout)
        form_layout.addStretch()
        main_layout.addLayout(form_layout, 3)

    def refresh_list(self):
        self.list_widget.clear()
        self.characters = self.library_service.get_characters()
        for char in self.characters:
            self.list_widget.addItem(char["name"])

    def on_selection_changed(self, index):
        if index < 0 or index >= len(self.characters):
            return
        char = self.characters[index]
        self.selected_character_id = char["id"]
        self.name_input.setText(char["name"])
        self.prompt_input.setPlainText(char["prompt_fragment"])
        self.desc_input.setText(char.get("description", ""))
        self.tags_input.setText(char.get("tags", ""))

    def clear_fields(self):
        self.selected_character_id = None
        self.name_input.clear()
        self.prompt_input.clear()
        self.desc_input.clear()
        self.tags_input.clear()
        self.list_widget.clearSelection()

    def save_character(self):
        name = self.name_input.text().strip()
        prompt = self.prompt_input.toPlainText().strip()
        desc = self.desc_input.text().strip()
        tags = self.tags_input.text().strip()
        
        if not name or not prompt:
            QMessageBox.warning(self, "Validation Error", "Name and Prompt fragment are required.")
            return
            
        if self.selected_character_id is None:
            self.library_service.create_character(name, desc, "", prompt, tags)
        else:
            # For simplicity, we recreate/delete in this basic library DB service, 
            # or update directly. We delete and recreate to save lines of code.
            self.library_service.delete_character(self.selected_character_id)
            self.library_service.create_character(name, desc, "", prompt, tags)
            
        self.refresh_list()
        self.clear_fields()
        QMessageBox.information(self, "Success", "Character saved successfully.")

    def delete_character(self):
        if self.selected_character_id is None:
            return
        self.library_service.delete_character(self.selected_character_id)
        self.refresh_list()
        self.clear_fields()
        QMessageBox.information(self, "Deleted", "Character deleted successfully.")

    def insert_prompt(self):
        prompt = self.prompt_input.toPlainText().strip()
        if prompt:
            event_bus.context_changed.emit({"append_prompt": prompt})
            self.accept()
