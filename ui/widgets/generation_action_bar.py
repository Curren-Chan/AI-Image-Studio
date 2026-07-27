"""Persistent generation controls for the Generation workspace.

This widget deliberately owns only the presentation and signals.  Removing the
feature later is a one-line change in MainWindow, without touching prompt or
queue logic.
"""

from time import monotonic

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QProgressBar

from core.event_bus import event_bus


class GenerationActionBar(QFrame):
    """Always-visible generate action and compact queue progress information."""

    generate_requested = Signal()

    def __init__(self, queue_service, parent=None):
        super().__init__(parent)
        self.queue_service = queue_service
        self._running_started_at = None
        self._running_job_id = None
        self._build_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(1_000)
        self._timer.timeout.connect(self._refresh_elapsed_time)
        self._timer.start()

        event_bus.queue_updated.connect(self.refresh)
        event_bus.job_status_changed.connect(self._on_job_status_changed)
        event_bus.status_updated.connect(self._on_status_updated)
        self.refresh()

    def _build_ui(self):
        self.setObjectName("generationActionBar")
        self.setStyleSheet(
            "#generationActionBar { background: #1e1e1e; border: 1px solid #3a3a3c; "
            "border-radius: 8px; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setMinimumHeight(42)
        self.generate_btn.setStyleSheet(
            "QPushButton { background-color: #5856d6; color: white; font-size: 14px; "
            "font-weight: bold; border-radius: 6px; border: none; padding: 0 24px; }"
            "QPushButton:hover { background-color: #6e6cf0; }"
            "QPushButton:disabled { background-color: #3a3a3c; color: #8e8e93; }"
        )
        self.generate_btn.clicked.connect(self.generate_requested.emit)
        layout.addWidget(self.generate_btn)

        self.progress_label = QLabel("Ready")
        self.progress_label.setMinimumWidth(220)
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumWidth(120)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.cancel_waiting_btn = QPushButton("Cancel waiting job")
        self.cancel_waiting_btn.setToolTip("Cancels the next waiting job. An in-progress API request cannot be interrupted.")
        self.cancel_waiting_btn.clicked.connect(self.cancel_next_waiting_job)
        layout.addWidget(self.cancel_waiting_btn)

    def set_generate_enabled(self, enabled: bool):
        self.generate_btn.setEnabled(enabled)

    def refresh(self):
        jobs = self.queue_service.get_jobs()
        running = next((job for job in jobs if job["status"] == "Running"), None)
        waiting = [job for job in jobs if job["status"] == "Pending"]

        if running:
            if self._running_job_id != running["id"]:
                self._running_job_id = running["id"]
                self._running_started_at = monotonic()
            self.progress_bar.show()
            self.progress_label.setText(
                f"Generating job #{running['id']} | {len(waiting)} waiting | {self._elapsed_text()}"
            )
        else:
            self._running_job_id = None
            self._running_started_at = None
            self.progress_bar.hide()
            self.progress_label.setText(f"Ready | {len(waiting)} waiting")

        self.cancel_waiting_btn.setEnabled(bool(waiting))

    def cancel_next_waiting_job(self):
        if self.queue_service.cancel_next_pending_job():
            event_bus.status_updated.emit("Cancelled the next waiting generation job.")

    def _on_job_status_changed(self, _job_id: int, _status: str):
        self.refresh()

    def _on_status_updated(self, message: str):
        if self._running_job_id and message:
            self.progress_label.setText(f"Generating job #{self._running_job_id} | {message} | {self._elapsed_text()}")

    def _refresh_elapsed_time(self):
        if self._running_job_id:
            self.refresh()

    def _elapsed_text(self) -> str:
        if self._running_started_at is None:
            return "0:00"
        elapsed = int(monotonic() - self._running_started_at)
        return f"{elapsed // 60}:{elapsed % 60:02d}"
