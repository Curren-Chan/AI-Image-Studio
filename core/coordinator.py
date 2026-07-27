import os
import logging
from database.connection import DbConnectionManager
from database.schema import setup_schema
from database.import_helper import import_legacy_history

from services.settings_service import SettingsService
from services.project_service import ProjectService
from services.prompt_service import PromptService
from services.template_service import TemplateService
from services.history_service import HistoryService
from services.gallery_service import GalleryService
from services.queue_service import QueueService
from services.undo_service import UndoService
from services.library_service import LibraryService
from services.plugin_service import PluginService
from services.vision_service import VisionService
from services.generation_service import GenerationService

from api.client import ApiClient
from api.vision_client import VisionClient

class Coordinator:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(
        self,
        project_root: str | None = None,
        start_consumer: bool = True,
        load_plugins: bool = True,
    ):
        logging.info("Initializing Coordinator Facade...")
        self._shutdown_requested = False
        
        # 1. Setup SQLite database connection & schemas
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.abspath(project_root)
        self.project_root = project_root
        db_path = os.path.join(project_root, "database.db")
        self.db_service = DbConnectionManager(db_path)
        
        # Initialize tables
        conn = self.db_service.get_connection()
        try:
            setup_schema(conn)
        finally:
            conn.close()

        # Run legacy history recovery in background thread to avoid blocking startup
        import threading
        output_dir = os.path.join(project_root, "outputs")
        def _bg_import():
            bg_conn = self.db_service.get_connection()
            try:
                import_legacy_history(bg_conn, output_dir)
            except Exception as e:
                logging.warning(f"Background legacy history import failed: {e}")
            finally:
                bg_conn.close()
        threading.Thread(target=_bg_import, daemon=True).start()
        
        # 2. Initialize Service Layer
        self.settings_service = SettingsService(self.db_service, project_root=project_root)
        self.project_service = ProjectService(self.db_service)
        self.prompt_service = PromptService(None, self.db_service) # api_client set below
        self.template_service = TemplateService(self.db_service, project_root=project_root)
        self.history_service = HistoryService(self.db_service)
        self.history_service.cleanup_duplicate_records()
        self.gallery_service = GalleryService(self.db_service)
        self.queue_service = QueueService(self.db_service)
        self.undo_service = UndoService(self.db_service)
        self.library_service = LibraryService(self.db_service)
        
        # 3. Setup API clients
        api_key = self.settings_service.get_api_key()
        fal_key = self.settings_service.get_fal_key()
        gemini_key = self.settings_service.get_gemini_key()
        xai_key = self.settings_service.get_xai_key()
        hotapi_key = self.settings_service.get_hotapi_key()
        self.api_client = ApiClient(api_key=api_key, fal_key=fal_key, gemini_key=gemini_key, xai_key=xai_key, hotapi_key=hotapi_key)

        # Inject API client to prompt_service
        self.prompt_service.api_client = self.api_client
        
        self.vision_client = VisionClient(self.api_client)
        
        # 4. Initialize Generation & Vision Services
        self.generation_service = GenerationService(
            self.api_client, 
            self.prompt_service, 
            self.history_service, 
            self.settings_service, 
            self.template_service,
            self.db_service,
            project_root=project_root,
        )
        self.vision_service = VisionService(self.vision_client, self.db_service)
        self.plugin_service = PluginService(self, self.db_service, project_root=project_root)
        
        # Start queue consumer thread
        if start_consumer:
            self.queue_service.start_consumer(self.generation_service)
        
        # Load custom plugins
        if load_plugins:
            self.plugin_service.load_plugins()
        logging.info("Coordinator Facade successfully initialized.")

    def shutdown(self, timeout_seconds: float | None = 0.0) -> bool:
        """Cleanly terminates background threads."""
        if not self._shutdown_requested:
            logging.info("Shutting down Coordinator Facade...")
            self._shutdown_requested = True
        stopped = self.queue_service.stop_consumer(timeout_seconds=timeout_seconds)
        if stopped:
            logging.info("Shutdown completed.")
        return stopped
