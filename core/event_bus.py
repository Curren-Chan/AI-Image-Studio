from PySide6.QtCore import QCoreApplication, QObject, Signal

class EventBus(QObject):
    # Image Generation & Queueing
    generation_requested = Signal(dict)      # params
    job_added = Signal(int)                  # job_id
    job_status_changed = Signal(int, str)    # job_id, status
    image_generated = Signal(dict)           # result metadata
    
    # Context & UI States
    context_changed = Signal(dict)           # loaded prompt/style/size/quality
    project_changed = Signal(int)            # project_id
    theme_changed = Signal(str)              # theme name ("Dark", "Light", "Auto")
    status_updated = Signal(str)             # status message
    progress_updated = Signal(int)           # progress percent
    
    # Data synchronizations
    gallery_refresh_requested = Signal()
    preset_updated = Signal()
    template_updated = Signal()
    queue_updated = Signal()
    model_config_changed = Signal()

# Production imports this module only after QApplication has been created.  By
# parenting the bus to the application, Qt destroys queued connections while
# the application is still alive instead of during late Python module cleanup.
event_bus = EventBus(QCoreApplication.instance())
