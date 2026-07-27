import tempfile
import unittest

from core.coordinator import Coordinator
from tests import TEST_APP
from ui.main_window import MainWindow


class RefactoredGuiTests(unittest.TestCase):
    def test_launch_with_isolated_services(self):
        with tempfile.TemporaryDirectory() as project_root:
            coordinator = Coordinator(
                project_root=project_root,
                start_consumer=False,
                load_plugins=False,
            )
            coordinator.api_client.mock_mode = True
            window = MainWindow(coordinator)
            window.show()
            TEST_APP.processEvents()
            self.assertIn("AI Image Studio Ver", window.windowTitle())
            window.close()
            TEST_APP.processEvents()
            self.assertFalse(window.isVisible())


if __name__ == "__main__":
    unittest.main()
