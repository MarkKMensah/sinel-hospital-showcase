class ResponseMessage:
    FAILED = "failed"
    ERROR = "error"
    SUCCESS = "success"

    def __init__(self, status, reason) -> None:
        self.status = status
        self.reason = reason

    def to_json(self):
        return {"status": self.status, "message": self.reason}
