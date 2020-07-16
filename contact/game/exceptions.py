class GameException(Exception):
    error_type = None

    def __init__(self, details):
        data = {"details": details, "error_type": self.error_type}
        self.data = data
        super().__init__()


class GameRuleError(GameException):
    error_type = "rule"


class GameActionError(GameException):
    error_type = "action"
