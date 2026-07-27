from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit, QPushButton, QLabel, QMessageBox
from core.event_bus import event_bus

class ProjectPanel(QWidget):
    def __init__(self, coordinator, parent=None):
        super().__init__(parent)
        self.coordinator = coordinator
        self.projects_list = []
        self.init_ui()
        self.refresh_list()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        layout.addWidget(QLabel("Project Workspaces (プロジェクト管理):"))
        
        # Project Lists
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.on_selection_changed)
        layout.addWidget(self.list_widget)
        
        # Form to add new project
        add_layout = QHBoxLayout()
        add_layout.setContentsMargins(0, 0, 0, 0)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter new project name... (例: キャラクター制作)")
        add_layout.addWidget(self.name_input, 3)
        
        self.btn_add = QPushButton("➕ Create Project")
        self.btn_add.clicked.connect(self.create_project)
        self.btn_add.setStyleSheet("background-color: #34c759; color: white;")
        add_layout.addWidget(self.btn_add, 1)
        
        layout.addLayout(add_layout)
        
        # Toolbar actions
        toolbar = QHBoxLayout()
        self.btn_switch = QPushButton("🔄 Switch Active Project")
        self.btn_switch.clicked.connect(self.switch_project)
        self.btn_switch.setStyleSheet("background-color: #007aff; color: white;")
        toolbar.addWidget(self.btn_switch)
        
        self.btn_delete = QPushButton("🗑️ Delete Project")
        self.btn_delete.clicked.connect(self.delete_project)
        self.btn_delete.setStyleSheet("background-color: #ff3b30; color: white;")
        toolbar.addWidget(self.btn_delete)
        
        layout.addLayout(toolbar)

    def refresh_list(self):
        self.list_widget.clear()
        self.projects_list = self.coordinator.project_service.get_projects()
        
        active_id = self.coordinator.project_service.get_active_project_id()
        for idx, proj in enumerate(self.projects_list):
            marker = " ✅ (Active)" if proj["id"] == active_id else ""
            self.list_widget.addItem(f"{proj['name']}{marker}")

    def on_selection_changed(self, index):
        pass

    def create_project(self):
        name = self.name_input.text().strip()
        if not name:
            return
        try:
            self.coordinator.project_service.create_project(name, "User created project")
            self.name_input.clear()
            self.refresh_list()
            QMessageBox.information(self, "Success", f"Project '{name}' created successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create project: {e}")

    def switch_project(self):
        idx = self.list_widget.currentRow()
        if idx < 0 or idx >= len(self.projects_list):
            return
        proj = self.projects_list[idx]
        self.coordinator.project_service.set_active_project(proj["id"])
        self.refresh_list()
        
        # Emit workspace changes
        event_bus.project_changed.emit(proj["id"])
        event_bus.gallery_refresh_requested.emit()
        event_bus.status_updated.emit(f"Switched project workspace to: {proj['name']}")

    def delete_project(self):
        idx = self.list_widget.currentRow()
        if idx < 0 or idx >= len(self.projects_list):
            return
        proj = self.projects_list[idx]

        if self.coordinator.queue_service.has_active_jobs(proj["id"]):
            QMessageBox.warning(
                self,
                "Project is in use",
                "This project has a pending or running generation job. Pause or finish the job before deleting the project.",
            )
            return
        
        # Standard default project cannot be deleted if it is the only one
        if len(self.projects_list) <= 1:
            QMessageBox.warning(self, "Warning", "Cannot delete the only remaining project workspace.")
            return
            
        ret = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete project '{proj['name']}'? Generates will be unlinked.",
            QMessageBox.Yes | QMessageBox.No
        )
        if ret == QMessageBox.Yes:
            self.coordinator.project_service.delete_project(proj["id"])
            self.refresh_list()
            event_bus.project_changed.emit(self.coordinator.project_service.get_active_project_id())
            event_bus.gallery_refresh_requested.emit()
            QMessageBox.information(self, "Deleted", f"Project workspace '{proj['name']}' deleted.")
