# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, 
    QTableWidgetItem, QTextBrowser, QHeaderView, QGroupBox, QSplitter
)
from PySide6.QtCore import Qt
from api.model_registry import MODEL_REGISTRY

class TipsPanel(QWidget):
    def __init__(self, coordinator, parent=None):
        super().__init__(parent)
        self.coordinator = coordinator
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Splitter to balance table and hints
        splitter = QSplitter(Qt.Horizontal)
        
        # 1. Left side: Cost Table Group
        table_group = QGroupBox("AI Models Pricing & Cost List (コスト一覧)")
        table_layout = QVBoxLayout(table_group)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Model Name", "Provider", "Category", "Cost ($ / image)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        table_layout.addWidget(self.table)
        splitter.addWidget(table_group)
        
        # 2. Right side: Tips & Guide Group
        guide_group = QGroupBox("Model Guidelines & Tips (モデル特徴とプロンプトのコツ)")
        guide_layout = QVBoxLayout(guide_group)
        
        self.guide_text = QTextBrowser()
        self.guide_text.setReadOnly(True)
        
        guide_layout.addWidget(self.guide_text)
        splitter.addWidget(guide_group)
        
        # Add splitter to main layout
        layout.addWidget(splitter)
        
        # Set splitter proportions (e.g. 55% table, 45% guide)
        splitter.setSizes([600, 450])
        
        # Populate content
        self.populate_table()
        self.populate_guide()

    def populate_table(self):
        # Gather registry models and sort by cost descending
        models = list(MODEL_REGISTRY.values())
        models.sort(key=lambda x: x["estimated_cost"], reverse=True)
        
        self.table.setRowCount(len(models))
        
        for idx, model in enumerate(models):
            # Model Display Name
            item_name = QTableWidgetItem(model["display_name"])
            item_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(idx, 0, item_name)
            
            # Provider
            prov = model["provider"].upper()
            if prov == "XAI":
                prov = "xAI (Direct)"
            elif prov == "FAL":
                prov = "fal.ai"
            item_prov = QTableWidgetItem(prov)
            item_prov.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.table.setItem(idx, 1, item_prov)
            
            # Category
            cat = model["category"]
            cat_str = "T2I & Edit" if cat == "both" else ("T2I Only" if cat == "text2img" else "Edit Only")
            item_cat = QTableWidgetItem(cat_str)
            item_cat.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.table.setItem(idx, 2, item_cat)
            
            # Estimated Cost
            cost = model["estimated_cost"]
            item_cost = QTableWidgetItem(f"${cost:.5f}")
            item_cost.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_cost.setForeground(Qt.green)
            self.table.setItem(idx, 3, item_cost)

    def populate_guide(self):
        html_content = """
        <h3>💡 各AIモデルの特徴と使い分け</h3>
        <hr>
        <p><b>1. OpenAI - GPT Image 2</b><br>
        非常に高度な指示追従性とディテール表現力を持ち、ネガティブプロンプトの記述もプロンプト内で再現可能です。文字入れや複雑な情景描写に強く、標準的な画像生成に最も推奨されます。</p>
        
        <p><b>2. fal.ai - FLUX.2 (Pro / Dev)</b><br>
        Black Forest Labs の次世代フラグシップモデル。フォトリアル描写、テクスチャの質感、さらに英語テキストの正確なスペル記述能力に非常に優れています。Pro版は最高品質、Dev版はややコストを抑えてディテールを出したい場合に適しています。</p>
        
        <p><b>3. fal.ai / xAI - Grok Imagine</b><br>
        Auroraアーキテクチャによる写実性とアート表現のバランスに長けたモデル。fal.ai経由（FAL_KEY）とxAI直接接続（XAI_API_KEY）の双方に対応しており、Grok特有のシャープでドラマチックなコントラストが得られます。</p>
        
        <p><b>4. fal.ai - Qwen Image 2.0</b><br>
        Alibabaが開発した高性能モデル。特に東洋美術、アニメ調、あるいは繊細なキャラクター表現において美しいイラストを描くことに長けています。</p>
        
        <p><b>5. fal.ai - Seedream 5.0 Pro</b><br>
        ByteDanceによる商用・プロダクション向け高品質画像生成/編集エンジン。細やかな編集、領域指定、高解像度の精密なアライメント処理に優れています。</p>
        
        <br>
        <h3>✍️ 美しいプロンプトを作るためのコツ</h3>
        <hr>
        <ul>
          <li><b>具体性を高める</b>: 単に「少女」とするより、「木漏れ日の中に立つ、青い瞳をした長い銀髪の少女」のように状況・光の差し方・属性を英語で具体的に指定します。</li>
          <li><b>安全バイパスの活用</b>: アプリに組み込まれた翻訳エンジン（OpenAI/Gemini）は「セクシー」などのNGワードを自動で芸術的な表現（elegant body lines等）に上品に翻訳してフィルター回避します。</li>
          <li><b>解像度とアスペクト比</b>: シネマティックな絵には 16:9、キャラクター全身には 9:16（GrokやFLUX.2等の比率指定）を選択すると構図が安定します。</li>
        </ul>
        """
        self.guide_text.setHtml(html_content)
