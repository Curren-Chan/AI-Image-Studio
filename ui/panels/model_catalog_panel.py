# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QScrollArea, QFrame, QCheckBox, QPushButton, QGridLayout
)
from PySide6.QtCore import Qt
from api.model_registry import MODEL_REGISTRY
from core.event_bus import event_bus


class ModelCatalogPanel(QWidget):
    """Model Catalog Panel for browsing, searching, filtering, and enabling AI models."""

    def __init__(self, coordinator, parent=None):
        super().__init__(parent)
        self.coordinator = coordinator
        self.card_widgets = {} # model_id -> dict of widgets
        self.current_theme = self.coordinator.settings_service.get_setting("theme", "Dark")
        self._initialized = False
        self.init_ui()
        
        event_bus.theme_changed.connect(self.on_theme_changed)
        self.apply_theme_styles()

    def ensure_initialized(self):
        """Lazy initializer called when Model Catalog tab is first shown."""
        if not self._initialized:
            self._initialized = True
            self.load_catalog()

    def on_theme_changed(self, theme_name: str):
        self.current_theme = theme_name
        self.apply_theme_styles()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)

        # 1. Top Header & Search/Filter Toolbar
        self.header_frame = QFrame()
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setSpacing(10)

        title_layout = QHBoxLayout()
        self.title_label = QLabel("🤖 AI Model Catalog")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.desc_label = QLabel("有効化するモデルを一覧から検索・切り替えできます。ONにしたモデルが生成画面の選択肢に反映されます。")
        self.desc_label.setStyleSheet("font-size: 12px;")
        title_layout.addWidget(self.title_label)
        title_layout.addSpacing(15)
        title_layout.addWidget(self.desc_label)
        title_layout.addStretch()
        header_layout.addLayout(title_layout)

        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 モデル名やエンドポイントを検索...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedHeight(34)
        self.search_input.textChanged.connect(self.filter_catalog)
        filter_layout.addWidget(self.search_input, 2)

        self.category_filter = QComboBox()
        self.category_filter.addItems(["すべてのカテゴリ (All)", "🎨 Text-to-Image", "✏️ Image Editing"])
        self.category_filter.setFixedHeight(34)
        self.category_filter.currentIndexChanged.connect(self.filter_catalog)
        filter_layout.addWidget(self.category_filter, 1)

        self.provider_filter = QComboBox()
        self.provider_filter.addItems(["すべてのプロバイダ (All)", "OpenAI", "fal.ai", "Grok (xAI)"])
        self.provider_filter.setFixedHeight(34)
        self.provider_filter.currentIndexChanged.connect(self.filter_catalog)
        filter_layout.addWidget(self.provider_filter, 1)

        self.tag_filter = QComboBox()
        self.tag_filter.addItems(["すべてのタグ (All)", "✨ 万能", "🎨 アニメイラスト向け", "📷 実写向け", "🔥 NSFW対応"])
        self.tag_filter.setFixedHeight(34)
        self.tag_filter.currentIndexChanged.connect(self.filter_catalog)
        filter_layout.addWidget(self.tag_filter, 1)

        self.btn_select_all = QPushButton("全選択")
        self.btn_select_all.setFixedHeight(34)
        self.btn_select_all.clicked.connect(self.select_all_models)
        filter_layout.addWidget(self.btn_select_all)

        header_layout.addLayout(filter_layout)
        main_layout.addWidget(self.header_frame)

        # 2. Scroll Area for Model Cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.cards_container = QWidget()
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setContentsMargins(0, 0, 0, 0)
        self.cards_grid.setSpacing(12)

        self.scroll_area.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll_area, 1)

    def load_catalog(self):
        # Clear existing
        for i in reversed(range(self.cards_grid.count())):
            item = self.cards_grid.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        self.card_widgets.clear()

        # Load currently enabled model IDs
        enabled_str = self.coordinator.settings_service.get_setting("enabled_models", "")
        if not enabled_str:
            enabled_str = self.coordinator.settings_service.defaults.get("enabled_models", "")
        enabled_ids = set([x.strip() for x in enabled_str.split(",") if x.strip()])

        row = 0
        col = 0
        max_cols = 2 # 2 columns grid for comfortable reading

        for model_id, model_meta in MODEL_REGISTRY.items():
            card = QFrame()
            card.setObjectName("modelCard")
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)

            # Set Mouseover Tooltip for model features & description
            desc_text = model_meta.get("description", "特徴情報が未定義です。")
            tooltip_content = f"<b>{model_meta['display_name']}</b><br><hr><b>【特徴・解説】</b><br>{desc_text}"
            card.setToolTip(tooltip_content)

            # Top row: Title & Tag Badges & Enable Checkbox
            top_row = QHBoxLayout()
            title = QLabel(model_meta["display_name"])
            title.setStyleSheet("font-size: 14px; font-weight: bold;")
            title.setToolTip(tooltip_content)
            top_row.addWidget(title)

            # Add Model Tags Badges
            tag_badges = []
            tags = model_meta.get("tags", [])
            for tag in tags:
                badge = QLabel(tag)
                badge.setToolTip(tooltip_content)
                top_row.addWidget(badge)
                tag_badges.append((badge, tag))

            top_row.addStretch()

            cb = QCheckBox("使用する (ON)")
            cb.setStyleSheet("QCheckBox { font-weight: bold; color: #007aff; }")
            cb.setChecked(model_id in enabled_ids)
            cb.setProperty("model_id", model_id)
            cb.stateChanged.connect(self.on_model_toggled)
            top_row.addWidget(cb)
            card_layout.addLayout(top_row)

            # Endpoint
            endpoint_lbl = QLabel(f"Endpoint: {model_meta.get('endpoint', 'N/A')}")
            endpoint_lbl.setStyleSheet("font-size: 11px; font-family: Consolas, monospace;")
            card_layout.addWidget(endpoint_lbl)

            # Description Summary Label (Smart Overview)
            desc_lbl = QLabel(desc_text)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("font-size: 11px; font-style: italic;")
            desc_lbl.setToolTip(tooltip_content)
            card_layout.addWidget(desc_lbl)

            # Properties Tag Bar
            tags_layout = QHBoxLayout()
            tags_layout.setSpacing(8)

            cat = model_meta.get("category", "text2img")
            cat_text = "🎨 Text-to-Image" if cat == "text2img" else ("✏️ Image Edit" if cat == "img_edit" else "🎨/✏️ Both")
            cat_badge = QLabel(cat_text)
            cat_badge.setStyleSheet("color: #007aff; background: rgba(0, 122, 255, 0.15); border-radius: 4px; padding: 2px 6px; font-size: 11px;")
            tags_layout.addWidget(cat_badge)

            cost = model_meta.get("estimated_cost", 0.0)
            cost_badge = QLabel(f"コスト目安: ${cost:.3f} / 枚")
            cost_badge.setStyleSheet("color: #34c759; background: rgba(52, 199, 89, 0.15); border-radius: 4px; padding: 2px 6px; font-size: 11px;")
            tags_layout.addWidget(cost_badge)

            neg_supp = model_meta.get("supports_negative_prompt", False)
            if neg_supp:
                neg_badge = QLabel("Negative Prompt OK")
                neg_badge.setStyleSheet("color: #8e8e93; background: rgba(142, 142, 147, 0.15); border-radius: 4px; padding: 2px 6px; font-size: 11px;")
                tags_layout.addWidget(neg_badge)

            tags_layout.addStretch()
            card_layout.addLayout(tags_layout)

            self.card_widgets[model_id] = {
                "card": card,
                "cb": cb,
                "meta": model_meta,
                "title": title,
                "endpoint_lbl": endpoint_lbl,
                "desc_lbl": desc_lbl,
                "tag_badges": tag_badges
            }
            self.cards_grid.addWidget(card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        self.apply_theme_styles()

    def apply_theme_styles(self):
        is_light = self.current_theme == "Light"

        # Header Frame
        if is_light:
            self.header_frame.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #c7c7cc; border-radius: 10px; padding: 8px 12px; }")
            self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #000000;")
            self.desc_label.setStyleSheet("font-size: 12px; color: #555559;")
        else:
            self.header_frame.setStyleSheet("QFrame { background: #1e1e1e; border: 1px solid #2c2c2e; border-radius: 10px; padding: 8px 12px; }")
            self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
            self.desc_label.setStyleSheet("font-size: 12px; color: #8e8e93;")

        # Cards
        for model_id, item in self.card_widgets.items():
            card = item["card"]
            title = item["title"]
            endpoint_lbl = item["endpoint_lbl"]
            desc_lbl = item["desc_lbl"]
            tag_badges = item["tag_badges"]

            if is_light:
                card.setStyleSheet(
                    "QFrame#modelCard { background: #ffffff; border: 1px solid #c7c7cc; border-radius: 10px; padding: 12px; }"
                    "QFrame#modelCard:hover { border-color: #007aff; }"
                )
                title.setStyleSheet("font-size: 14px; font-weight: bold; color: #000000;")
                endpoint_lbl.setStyleSheet("color: #636366; font-size: 11px; font-family: Consolas, monospace;")
                desc_lbl.setStyleSheet("color: #48484a; font-size: 11px; font-style: italic;")
            else:
                card.setStyleSheet(
                    "QFrame#modelCard { background: #1e1e1e; border: 1px solid #2c2c2e; border-radius: 10px; padding: 12px; }"
                    "QFrame#modelCard:hover { border-color: #0a84ff; }"
                )
                title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
                endpoint_lbl.setStyleSheet("color: #8e8e93; font-size: 11px; font-family: Consolas, monospace;")
                desc_lbl.setStyleSheet("color: #a1a1aa; font-size: 11px; font-style: italic;")

            # Style tag badges
            for badge, tag_name in tag_badges:
                if tag_name == "万能":
                    style = "color: #ffffff; background: #a855f7; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
                elif tag_name == "アニメイラスト向け":
                    style = "color: #ffffff; background: #ec4899; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
                elif tag_name == "実写向け":
                    style = "color: #ffffff; background: #3b82f6; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
                elif tag_name == "NSFW対応":
                    style = "color: #ffffff; background: #f97316; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
                else:
                    style = "color: #ffffff; background: #64748b; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
                badge.setStyleSheet(style)

    def filter_catalog(self):
        search_term = self.search_input.text().strip().lower()
        cat_idx = self.category_filter.currentIndex()
        prov_idx = self.provider_filter.currentIndex()
        tag_idx = self.tag_filter.currentIndex()

        prov_map = {1: "openai", 2: "fal", 3: "xai"}
        tag_map = {1: "万能", 2: "アニメイラスト向け", 3: "実写向け", 4: "NSFW対応"}

        for model_id, item in self.card_widgets.items():
            card = item["card"]
            meta = item["meta"]
            
            # Text search
            match_search = not search_term or (
                search_term in meta["display_name"].lower() or 
                search_term in meta["endpoint"].lower() or
                search_term in meta.get("description", "").lower()
            )
            
            # Category match
            cat = meta.get("category", "text2img")
            match_cat = True
            if cat_idx == 1: # T2I
                match_cat = cat in ("text2img", "both")
            elif cat_idx == 2: # Edit
                match_cat = cat in ("img_edit", "both")

            # Provider match
            match_prov = True
            if prov_idx in prov_map:
                match_prov = meta.get("provider") == prov_map[prov_idx]

            # Tag match
            match_tag = True
            if tag_idx in tag_map:
                target_tag = tag_map[tag_idx]
                match_tag = target_tag in meta.get("tags", [])

            card.setVisible(match_search and match_cat and match_prov and match_tag)

    def on_model_toggled(self, state):
        enabled_ids = []
        for model_id, item in self.card_widgets.items():
            cb = item["cb"]
            if cb.isChecked():
                enabled_ids.append(model_id)

        # Enforce at least 1 default if user turns off everything
        if not enabled_ids:
            enabled_ids = ["openai-gpt-image-2"]
            if "openai-gpt-image-2" in self.card_widgets:
                item = self.card_widgets["openai-gpt-image-2"]
                cb = item["cb"]
                cb.blockSignals(True)
                cb.setChecked(True)
                cb.blockSignals(False)

        enabled_str = ",".join(enabled_ids)
        self.coordinator.settings_service.save_setting("enabled_models", enabled_str)
        event_bus.model_config_changed.emit()
        event_bus.status_updated.emit("Model Catalog configuration updated.")

    def select_all_models(self):
        changed = False
        for item in self.card_widgets.values():
            card = item["card"]
            cb = item["cb"]
            if card.isVisible() and not cb.isChecked():
                cb.blockSignals(True)
                cb.setChecked(True)
                cb.blockSignals(False)
                changed = True
        if changed:
            self.on_model_toggled(Qt.Checked)
