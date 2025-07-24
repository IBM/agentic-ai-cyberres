import logging

logging.basicConfig(level=logging.INFO)
audit_logger = logging.getLogger("audit")

class AuditLoggingAgent:
    def __init__(self):
        pass

    def log_start(self, context: str):
        audit_logger.info(f"Audit log: Starting processing - {context}")

    def log_rejection(self, context: str, reason: str):
        audit_logger.info(f"Audit log: Rejected input - {context}. Reason: {reason}")

    def log_success(self, context: str):
        audit_logger.info(f"Audit log: Successfully processed - {context}")

    def log_event(self, context: str, event: str):
        audit_logger.info(f"Audit log: {context} - {event}")

if __name__ == "__main__":
    agent = AuditLoggingAgent()
    agent.log_start("Test context")
    agent.log_rejection("Test context", "Test reason")
    agent.log_success("Test context")
    agent.log_event("Test context", "Custom event message")
