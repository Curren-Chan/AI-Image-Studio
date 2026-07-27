# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QLineEdit
)
import json

class ExpertModelPanel(QWidget):
    """
    A widget that displays expert parameters for a specific AI model.
    Reads 'expert_params' from the model registry and dynamically creates input fields.
    """
    def __init__(self, model_id, model_meta, parent=None):
        super().__init__(parent)
        self.model_id = model_id
        self.model_meta = model_meta
        self.inputs = {}  # parameter_name -> widget
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        expert_params = self.model_meta.get("expert_params", [])
        
        if not expert_params:
            lbl = QLabel("No expert parameters available for this model.")
            lbl.setStyleSheet("color: #8e8e93; font-style: italic;")
            layout.addWidget(lbl)
            layout.addStretch()
            return

        for param in expert_params:
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            
            label = QLabel(param.get("label", param["name"]) + ":")
            label.setFixedWidth(120)
            row_layout.addWidget(label)
            
            p_type = param.get("type", "string")
            widget = None
            
            if p_type == "select":
                widget = QComboBox()
                for opt in param.get("options", []):
                    widget.addItem(opt["label"], opt["value"])
                default_val = param.get("default")
                if default_val is not None:
                    idx = widget.findData(default_val)
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
            
            elif p_type == "integer":
                # Using QLineEdit instead of QSpinBox so we can allow empty values (for 'Random')
                widget = QLineEdit()
                placeholder = param.get("placeholder", "")
                widget.setPlaceholderText(placeholder)
                default_val = param.get("default")
                if default_val is not None:
                    widget.setText(str(default_val))
                    
            elif p_type == "float":
                widget = QLineEdit()
                placeholder = param.get("placeholder", "")
                widget.setPlaceholderText(placeholder)
                default_val = param.get("default")
                if default_val is not None:
                    widget.setText(str(default_val))
            else:
                widget = QLineEdit()
                
            widget.setFixedHeight(30)
            row_layout.addWidget(widget)
            self.inputs[param["name"]] = {"widget": widget, "meta": param}
            
            layout.addLayout(row_layout)
            
        layout.addStretch()

    def get_expert_params_json(self) -> str | None:
        """Returns JSON string of the configured expert parameters, or None if none."""
        if not self.inputs:
            return None
            
        result = {}
        for name, data in self.inputs.items():
            widget = data["widget"]
            meta = data["meta"]
            p_type = meta.get("type")
            
            val = None
            if p_type == "select":
                val = widget.currentData()
            else:
                val = widget.text().strip()
                if val == "":
                    val = None
            
            result[name] = val
            
        return json.dumps(result)

    def set_expert_params(self, params: dict | str):
        """Restores the values of the expert widgets from a JSON string or dict."""
        if not params:
            return
            
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except Exception:
                return
                
        if not isinstance(params, dict):
            return
            
        for name, val in params.items():
            if name not in self.inputs:
                continue
                
            data = self.inputs[name]
            widget = data["widget"]
            meta = data["meta"]
            p_type = meta.get("type")
            
            if p_type == "select":
                if val is not None:
                    # QComboBox findData requires exact type matching or string mapping
                    idx = widget.findData(str(val))
                    if idx < 0:
                        # Fallback to direct text if data binding is simple string
                        idx = widget.findText(str(val))
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
            else:
                if val is not None:
                    widget.setText(str(val))
                else:
                    widget.clear()
