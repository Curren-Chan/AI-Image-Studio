import logging

class Command:
    def execute(self):
        raise NotImplementedError
    def undo(self):
        raise NotImplementedError

class UndoService:
    def __init__(self, db_service=None):
        self.db_service = db_service
        self.undo_stack = []
        self.redo_stack = []

    def execute_command(self, command: Command):
        try:
            command.execute()
            self.undo_stack.append(command)
            self.redo_stack.clear()
            logging.info(f"Executed command: {command.__class__.__name__}")
        except Exception as e:
            logging.error(f"Failed to execute command: {e}")
            raise e

    def undo(self) -> bool:
        if not self.undo_stack:
            logging.info("Undo stack is empty.")
            return False
            
        command = self.undo_stack.pop()
        try:
            command.undo()
            self.redo_stack.append(command)
            logging.info(f"Undone command: {command.__class__.__name__}")
            return True
        except Exception as e:
            logging.error(f"Failed to undo command: {e}")
            self.undo_stack.append(command)
            return False

    def redo(self) -> bool:
        if not self.redo_stack:
            logging.info("Redo stack is empty.")
            return False
            
        command = self.redo_stack.pop()
        try:
            command.execute()
            self.undo_stack.append(command)
            logging.info(f"Redone command: {command.__class__.__name__}")
            return True
        except Exception as e:
            logging.error(f"Failed to redo command: {e}")
            self.redo_stack.append(command)
            return False
