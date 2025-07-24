import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleSystemInspectionAgent:
    def __init__(self):
        pass

    def process_command(self, command: str) -> str:
        logger.info("Starting processing of command for audit logging")

        # Guardrail: Validate input type and content
        if not isinstance(command, str):
            logger.error("Input must be a string")
            logger.info("Audit log: Rejected input - not a string")
            return "Error: Input must be a string."
        if not command.strip():
            logger.error("Input command is empty")
            logger.info("Audit log: Rejected input - empty command")
            return "Error: Input command is empty."

        # Guardrail: Ethical check - simple keyword filter
        disallowed_keywords = ['hate', 'violence', 'terrorism', 'illegal', 'abuse']
        lower_command = command.lower()
        if any(keyword in lower_command for keyword in disallowed_keywords):
            logger.warning("Input contains disallowed content related to ethics")
            logger.info("Audit log: Rejected input - disallowed ethical content")
            return "Error: Input contains disallowed or unethical content and will not be processed."

        # Guardrail: Profanity filter (example list)
        profanity_keywords = ['damn', 'hell', 'crap']
        if any(word in lower_command for word in profanity_keywords):
            logger.warning("Input contains profanity")
            logger.info("Audit log: Rejected input - profanity detected")
            return "Error: Input contains inappropriate language and will not be processed."

        # Guardrail: Check for excessive punctuation
        punctuation_count = sum(command.count(c) for c in ['!', '?', '.', ',', ';', ':'])
        if punctuation_count > 100:
            logger.warning("Input contains excessive punctuation")
            logger.info("Audit log: Rejected input - excessive punctuation")
            return "Error: Input contains excessive punctuation and may be spam."

        # Guardrail: Check for repeated characters (e.g., more than 5 in a row)
        if re.search(r'(.)\1{5,}', command):
            logger.warning("Input contains repeated characters")
            logger.info("Audit log: Rejected input - repeated characters")
            return "Error: Input contains repeated characters and may be spam."

        # Guardrail: Limit number of sentences
        sentence_count = command.count('.') + command.count('!') + command.count('?')
        if sentence_count > 50:
            logger.warning("Input contains too many sentences")
            logger.info("Audit log: Rejected input - too many sentences")
            return "Error: Input contains too many sentences."

        # Guardrail: Limit input length to prevent excessive processing
        max_length = 1000
        if len(command) > max_length:
            logger.warning(f"Input command too long ({len(command)} chars), truncating to {max_length} chars")
            logger.info(f"Audit log: Input truncated from {len(command)} to {max_length} characters")
            command = command[:max_length]

        # Guardrail: Check for allowed system inspection commands keywords
        allowed_keywords = ['process', 'port', 'email', 'validate', 'system', 'status', 'check', 'running']
        if not any(keyword in lower_command for keyword in allowed_keywords):
            logger.warning("Input does not contain allowed system inspection related content")
            logger.info("Audit log: Rejected input - not related to system inspection commands")
            return "Error: Input does not appear to be related to system inspection or validation commands."

        # Simple processing: count words and sentences
        word_count = len(command.split())
        sentence_count = command.count('.') + command.count('!') + command.count('?')

        result = (
            f"Processed system inspection command:\n"
            f"Word count: {word_count}\n"
            f"Sentence count: {sentence_count}\n"
        )
        logger.info("System inspection command processed successfully")
        logger.info("Audit log: Successfully processed command")
        return result

if __name__ == "__main__":
    agent = SimpleSystemInspectionAgent()

    print("Please enter a system inspection or validation command for processing:")
    user_input = input()

    output = agent.process_command(user_input)
    print(output)
