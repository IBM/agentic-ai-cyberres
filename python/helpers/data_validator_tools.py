import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StringToolOutput:
    def __init__(self, value: str):
        if not isinstance(value, str):
            raise ValueError("StringToolOutput value must be a string")
        self.value = value

class FindRunningProcessesTool:
    name = "FindRunningProcesses"
    description = "Determine what applications are running on the system by looking at running processes. Disregard processes that are used by typical Linux system processes."

    def __init__(self):
        pass

    def handler(self, input):
        if not isinstance(input, dict):
            logger.error("Input must be a dictionary")
            return StringToolOutput("Validation Failed. Input must be a dictionary.")
        try:
            # Validate input keys if any expected (none expected here)
            stdout = subprocess.check_output(['ps', '-ax', '-o', 'pid,ppid,command'], text=True)
            logger.info("FindRunningProcessesTool executed successfully")
            return StringToolOutput(stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Command execution failed: {e}")
            return StringToolOutput(f"Validation Failed. Details:\n{e.output}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return StringToolOutput(f"Validation Failed. Unexpected error: {str(e)}")

class MongoDBDataValidatorTool:
    name = "MongoDBDataValidator"
    description = "This tool validates a mongodb database to ensure the database is not corrupted. Do not use this tool to validate anything that is not mongoDB. It can only be used if mongoDB is currently running."

    def __init__(self):
        pass

    def handler(self, input):
        if not isinstance(input, dict):
            logger.error("Input must be a dictionary")
            return StringToolOutput("Validation Failed. Input must be a dictionary.")
        argument = input.get("argument", "")
        if not isinstance(argument, str):
            logger.error("Argument must be a string")
            return StringToolOutput("Validation Failed. Argument must be a string.")
        if argument != "mongodb":
            logger.warning(f"Invalid argument for MongoDBDataValidatorTool: {argument}")
            return StringToolOutput(f"Validation Failed. Reason: {argument} cannot be used to validate mongodb")
        try:
            stdout = subprocess.check_output(['mongosh', '--file', 'src/helpers/mongoDBDataValidator.js'], text=True)
            logger.info("MongoDBDataValidatorTool executed successfully")
            return StringToolOutput(stdout)
        except FileNotFoundError:
            logger.error("mongosh command not found")
            return StringToolOutput("Validation Failed. mongosh command not found. Please install mongosh and ensure it is in your PATH.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Command execution failed: {e}")
            return StringToolOutput(f"Validation Failed. Details:\n{e.output}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return StringToolOutput(f"Validation Failed. Unexpected error: {str(e)}")

class SendEmailTool:
    name = "SendEmail"
    description = "Send an email."

    def __init__(self):
        self.email = os.getenv("USER_EMAIL")
        if not self.email:
            logger.warning("USER_EMAIL environment variable is not set")

    def handler(self, input):
        if not isinstance(input, dict):
            logger.error("Input must be a dictionary")
            return StringToolOutput("Validation Failed. Input must be a dictionary.")
        argument = input.get("argument", "")
        if not isinstance(argument, str):
            logger.error("Argument must be a string")
            return StringToolOutput("Validation Failed. Argument must be a string.")
        if not self.email:
            logger.error("USER_EMAIL environment variable not set")
            return StringToolOutput("Validation Failed. USER_EMAIL environment variable not set.")
        try:
            sendmail_input = f"Subject:Data Validation\n{argument}\n"
            process = subprocess.Popen(['sendmail', '-t', self.email], stdin=subprocess.PIPE, text=True)
            process.communicate(sendmail_input)
            if process.returncode != 0:
                logger.error(f"sendmail command failed with return code {process.returncode}")
                return StringToolOutput(f"Validation Failed. sendmail command failed with return code {process.returncode}")
            logger.info("SendEmailTool executed successfully")
            return StringToolOutput("Email sent successfully.")
        except FileNotFoundError:
            logger.error("sendmail command not found")
            return StringToolOutput("Validation Failed. sendmail command not found. Please install sendmail and ensure it is in your PATH.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return StringToolOutput(f"Validation Failed. Unexpected error: {str(e)}")

class FindWhatsRunningByPortsTool:
    name = "FindWhatsRunningByPorts"
    description = "Determine what applications are running on the system by looking at open listening ports. Disregard ports that are used by typical Linux system processes."

    def __init__(self):
        pass

    def handler(self, input):
        if not isinstance(input, dict):
            logger.error("Input must be a dictionary")
            return StringToolOutput("Validation Failed. Input must be a dictionary.")
        try:
            stdout = subprocess.check_output(['netstat', '-al'], text=True)
            logger.info("FindWhatsRunningByPortsTool executed successfully")
            return StringToolOutput(stdout)
        except FileNotFoundError:
            logger.error("netstat command not found")
            return StringToolOutput("Validation Failed. netstat command not found. Please install netstat and ensure it is in your PATH.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Command execution failed: {e}")
            return StringToolOutput(f"Validation Failed. Details:\n{e.output}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return StringToolOutput(f"Validation Failed. Unexpected error: {str(e)}")
