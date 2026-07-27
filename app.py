import sys
import logging
import os
import faulthandler
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QLockFile, QStandardPaths
from utils.logger import setup_logger
from core.version import APP_VERSION


_fault_log = None


def _install_exception_logging():
    """Keep Python and native crash diagnostics outside the Qt callback stack."""
    global _fault_log

    def log_unhandled(exc_type, exc_value, exc_traceback):
        logging.critical(
            "Unhandled application exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = log_unhandled

    def log_thread_exception(args):
        log_unhandled(args.exc_type, args.exc_value, args.exc_traceback)

    import threading

    threading.excepthook = log_thread_exception
    try:
        project_root = os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.join(project_root, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        _fault_log = open(
            os.path.join(logs_dir, "native_crash_trace.log"),
            "a",
            encoding="utf-8",
        )
        faulthandler.enable(_fault_log, all_threads=True)
    except OSError as exc:
        logging.warning("Could not enable native crash tracing: %s", exc)

def main():
    # Setup root logging output handlers
    setup_logger()
    _install_exception_logging()
    logging.info(f"Starting AI Image Studio Ver{APP_VERSION} Application...")
    
    app = QApplication(sys.argv)

    # Prevent a second process from pausing/claiming the first process's jobs.
    lock_path = os.path.join(
        QStandardPaths.writableLocation(QStandardPaths.TempLocation),
        "gpt_image_studio.lock",
    )
    instance_lock = QLockFile(lock_path)
    if not instance_lock.tryLock(0):
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.warning(
            None,
            "AI Image Studio",
            "AI Image Studio is already running.",
        )
        return 1

    # These imports create the global EventBus QObject, so they must happen
    # after QApplication exists.
    from core.coordinator import Coordinator
    from ui.main_window import MainWindow
    
    try:
        coordinator = Coordinator.get_instance()
        app.aboutToQuit.connect(lambda: coordinator.shutdown(timeout_seconds=None))
        window = MainWindow(coordinator)
        window.show()
    except Exception as exc:
        logging.exception("Application initialization failed")
        if "coordinator" in locals():
            coordinator.shutdown(timeout_seconds=2.0)
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.critical(
            None,
            "AI Image Studio startup error",
            f"The application could not start safely.\n\n{exc}",
        )
        instance_lock.unlock()
        return 1
    
    exit_code = app.exec()
    instance_lock.unlock()
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
