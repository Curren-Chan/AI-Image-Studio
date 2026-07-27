import os
import importlib.util
import logging
from services.base import BaseService

class PluginService(BaseService):
    def __init__(self, coordinator, db_service=None, project_root: str | None = None):
        super().__init__(db_service)
        self.coordinator = coordinator
        self.plugins: dict[str, object] = {}
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.plugins_dir = os.path.join(project_root, "plugins")
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
            
    def load_plugins(self):
        logging.info("Scanning plugins directory for plugins...")
        for file in os.listdir(self.plugins_dir):
            if file.endswith(".py") and file != "__init__.py" and file != "base.py":
                plugin_name = file[:-3]
                plugin_path = os.path.join(self.plugins_dir, file)
                
                try:
                    spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                    if spec is None or spec.loader is None:
                        continue
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, "Plugin"):
                        plugin_class = getattr(module, "Plugin")
                        plugin_instance = plugin_class(self.coordinator)
                        plugin_instance.activate()
                        self.plugins[plugin_name] = plugin_instance
                        logging.info(f"Successfully loaded and activated plugin: {plugin_name}")
                except Exception as e:
                    logging.error(f"Failed to load plugin {plugin_name}: {e}")
