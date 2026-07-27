import logging
from plugins.base import BasePlugin

class Plugin(BasePlugin):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        
    def activate(self):
        logging.info("Mock Generator Plugin activated successfully.")
        
    def deactivate(self):
        logging.info("Mock Generator Plugin deactivated.")
