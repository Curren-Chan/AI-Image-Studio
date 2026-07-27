from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QMessageBox, QLabel
from PySide6.QtCore import Qt
from core.event_bus import event_bus

class QueuePanel(QWidget):
    def __init__(self, coordinator, parent=None):
        super().__init__(parent)
        self.coordinator = coordinator
        self.init_ui()
        self.refresh_queue()
        
        # Connect signals
        event_bus.queue_updated.connect(self.refresh_queue)
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        layout.addWidget(QLabel("Job Queue Manager (バックグラウンド生成キュー):"))
        
        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "Status", "Prompt (JP)", "Style", "Size", "Quality", "Batch Count", "Created At"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)
        
        # Action Toolbar
        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 Refresh Queue")
        self.btn_refresh.clicked.connect(self.refresh_queue)
        toolbar.addWidget(self.btn_refresh)

        self.btn_resume = QPushButton("▶️ Resume / Run Selected Job")
        self.btn_resume.clicked.connect(self.resume_selected_job)
        toolbar.addWidget(self.btn_resume)

        self.btn_delete = QPushButton("🗑️ Cancel / Delete Job")
        self.btn_delete.clicked.connect(self.delete_selected_job)
        self.btn_delete.setStyleSheet("background-color: #ff3b30; color: white;")
        toolbar.addWidget(self.btn_delete)
        
        layout.addLayout(toolbar)

    def refresh_queue(self):
        self.table.setRowCount(0)
        jobs = self.coordinator.queue_service.get_jobs()
        
        for job in jobs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Populate columns
            self.table.setItem(row, 0, QTableWidgetItem(str(job["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(str(job["status"] or "")))
            self.table.setItem(row, 2, QTableWidgetItem(str(job["prompt_jp"] or "")))
            self.table.setItem(row, 3, QTableWidgetItem(str(job["style"] or "")))
            self.table.setItem(row, 4, QTableWidgetItem(str(job["size"] or "")))
            self.table.setItem(row, 5, QTableWidgetItem(str(job["quality"] or "")))
            self.table.setItem(row, 6, QTableWidgetItem(str(job["batch_count"])))
            self.table.setItem(row, 7, QTableWidgetItem(str(job["created_at"] or "")))
            
            # Read-only cells
            for col in range(8):
                item = self.table.item(row, col)
                if item:
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)

    def resume_selected_job(self):
        row = self.table.currentRow()
        if row < 0:
            return

        job_id_str = self.table.item(row, 0).text()
        job_id = int(job_id_str)
        status = self.table.item(row, 1).text()
        if status not in ("Paused", "Failed", "Cancelled"):
            QMessageBox.warning(
                self,
                "Cannot resume",
                f"Job {job_id} is {status} and cannot be resumed.",
            )
            return
        if not self.coordinator.queue_service.resume_job(job_id):
            QMessageBox.warning(
                self, "Cannot resume", "The job status changed before it could be resumed."
            )
        self.refresh_queue()

    def delete_selected_job(self):
        row = self.table.currentRow()
        if row < 0:
            return
            
        job_id_str = self.table.item(row, 0).text()
        job_id = int(job_id_str)
        status = self.table.item(row, 1).text()
        if status == "Running":
            QMessageBox.warning(
                self,
                "Cannot delete",
                "A running job cannot be deleted. Wait for it to finish or close the application to pause it safely.",
            )
            return
        
        ret = QMessageBox.question(
            self, "Cancel Job", 
            f"Are you sure you want to cancel and delete Job {job_id}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ret == QMessageBox.Yes:
            if not self.coordinator.queue_service.delete_job(job_id):
                QMessageBox.warning(
                    self,
                    "Delete failed",
                    "The job changed state and was not deleted.",
                )
                self.refresh_queue()
                return
            self.refresh_queue()
            QMessageBox.information(self, "Cancelled", f"Job {job_id} deleted successfully.")
