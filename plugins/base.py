class BasePlugin:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        
    def activate(self):
        raise NotImplementedError
        
    def deactivate(self):
        raise NotImplementedError
