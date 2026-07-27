from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Slot, QTimer
from core.event_bus import event_bus

class StatusPanel(QFrame):
    def __init__(self, coordinator, parent=None):
        super().__init__(parent)
        self.coordinator = coordinator
        self.init_ui()
        
        # Setup Blink Timer for Now Generating state
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.toggle_blink)
        self.is_blinking_visible = True
        self.last_status_msg = "Ready"
        
        self.update_status()
        
        # Subscribe to EventBus
        event_bus.status_updated.connect(self.set_status_message)
        event_bus.progress_updated.connect(self.set_progress_value)
        event_bus.queue_updated.connect(self.update_status)
        event_bus.project_changed.connect(self.update_status)
        event_bus.preset_updated.connect(self.update_status)
        
    def init_ui(self):
        self.setFixedHeight(30)
        self.setObjectName("StatusPanel")
        self.setStyleSheet("background-color: #1c1c1e; border-top: 1px solid #2c2c2e;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(15)
        
        # Status text message
        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("color: #8e8e93; font-size: 11px;")
        layout.addWidget(self.status_lbl, 2)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setStyleSheet("QProgressBar { border: 1px solid #2c2c2e; border-radius: 3px; background-color: #2c2c2e; text-align: center; color: transparent; } QProgressBar::chunk { background-color: #34c759; }")
        layout.addWidget(self.progress_bar)
        
        # Queue count
        self.queue_lbl = QLabel("Queue: 0 jobs")
        self.queue_lbl.setStyleSheet("color: #ff9500; font-size: 11px; font-weight: bold;")
        layout.addWidget(self.queue_lbl)
        
        # Project status
        self.project_lbl = QLabel("Project: Default Project")
        self.project_lbl.setStyleSheet("color: #5856d6; font-size: 11px; font-weight: bold;")
        layout.addWidget(self.project_lbl)
        
        # Connection status
        self.conn_lbl = QLabel("🟡 Mock Mode")
        self.conn_lbl.setStyleSheet("font-size: 11px; font-weight: bold;")
        layout.addWidget(self.conn_lbl)
        
        # Balance status (OpenAI, fal.ai, Grok)
        self.balance_lbl = QLabel("OpenAI: $10.00 | fal.ai: $10.00 | Grok: $10.00")
        self.balance_lbl.setStyleSheet("color: #34c759; font-size: 11px; font-weight: bold;")
        layout.addWidget(self.balance_lbl)

    @Slot(str)
    def set_status_message(self, msg: str):
        if msg.startswith("Generating job "):
            if msg != "Now Generating":
                self.last_status_msg = msg
            if not self.blink_timer.isActive():
                self.is_blinking_visible = True
                self.status_lbl.setText("Now Generating")
                self.status_lbl.setStyleSheet("color: #007aff; font-size: 11px; font-weight: bold;")
                self.blink_timer.start(500)
            self.update_status()
            return
            
        # Any other message (e.g. completion or error) stops the blink timer
        if self.blink_timer.isActive():
            self.blink_timer.stop()
            
        self.last_status_msg = msg
        self.status_lbl.setText(msg)
        if "error" in msg.lower() or "fail" in msg.lower():
            self.status_lbl.setStyleSheet("color: #ff3b30; font-size: 11px;")
        else:
            self.status_lbl.setStyleSheet("color: #8e8e93; font-size: 11px;")
            
        self.update_status()

    @Slot(int)
    def set_progress_value(self, val: int):
        if val < 0 or val >= 100:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
        else:
            self.progress_bar.setValue(val)

    def update_status(self, arg=None):
        # 1. Update Connection Label
        if self.coordinator.api_client.mock_mode:
            self.conn_lbl.setText("🟡 Mock Mode (Offline)")
            self.conn_lbl.setStyleSheet("color: #ff9500; font-size: 11px; font-weight: bold;")
        else:
            self.conn_lbl.setText("🟢 Connected")
            self.conn_lbl.setStyleSheet("color: #34c759; font-size: 11px; font-weight: bold;")
            
        # 2. Update Balances
        bal_openai = self.coordinator.settings_service.get_setting("balance_openai", "10.00")
        bal_fal = self.coordinator.settings_service.get_setting("balance_fal", "10.00")
        bal_grok = self.coordinator.settings_service.get_setting("balance_grok", "10.00")
        try:
            val_o = float(bal_openai)
            val_f = float(bal_fal)
            val_g = float(bal_grok)
            self.balance_lbl.setText(f"OpenAI: ${val_o:.2f}  |  fal.ai: ${val_f:.2f}  |  Grok: ${val_g:.2f}")
        except Exception:
            self.balance_lbl.setText(f"OpenAI: ${bal_openai}  |  fal: ${bal_fal}  |  Grok: ${bal_grok}")
            
        # 3. Update Queue Label
        jobs = self.coordinator.queue_service.get_jobs()
        pending_count = sum(1 for j in jobs if j["status"] in ("Pending", "Running"))
        self.queue_lbl.setText(f"Queue: {pending_count} active")
        
        # 4. Update Project Workspace Label
        projects = self.coordinator.project_service.get_projects()
        active_id = self.coordinator.project_service.get_active_project_id()
        for p in projects:
            if p["id"] == active_id:
                self.project_lbl.setText(f"Project: {p['name']}")
                break

    def toggle_blink(self):
        if self.is_blinking_visible:
            # Generate state is active, blink color (toggle transparent vs blue)
            self.status_lbl.setStyleSheet("color: #007aff; font-size: 11px; font-weight: bold;")
        else:
            self.status_lbl.setStyleSheet("color: transparent; font-size: 11px; font-weight: bold;")
        self.is_blinking_visible = not self.is_blinking_visible
