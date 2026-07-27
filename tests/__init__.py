import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication


# Ensure the production-global EventBus is created after a Qt application in
# every test order.
TEST_APP = QApplication.instance() or QApplication([])
