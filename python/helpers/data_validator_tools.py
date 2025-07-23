import subprocess
import os

class StringToolOutput:
    def __init__(self, value: str):
        self.value = value

class FindRunningProcessesTool:
    name = "FindRunningProcesses"
    description = "Determine what applications are running on the system by looking at running processes. Disregard processes that are used by typical Linux system processes."

    def __init__(self):
        pass

    def handler(self, input):
        try:
            stdout = subprocess.check_output(['ps', '--ppid', '2', '-p', '2', '--deselect'], text=True)
            return StringToolOutput(stdout)
        except subprocess.CalledProcessError as e:
            return StringToolOutput(f"Validation Failed. Details:\n{e.output}")

class MongoDBDataValidatorTool:
    name = "MongoDBDataValidator"
    description = "This tool validates a mongodb database to ensure the database is not corrupted. Do not use this tool to validate anything that is not mongoDB. It can only be used if mongoDB is currently running."

    def __init__(self):
        pass

    def handler(self, input):
        argument = input.get("argument", "")
        if argument != "mongodb":
            return StringToolOutput(f"Validation Failed. Reason: {argument} cannot be used to validate mongodb")
        try:
            stdout = subprocess.check_output(['mongosh', '--file', 'src/helpers/mongoDBDataValidator.js'], text=True)
            return StringToolOutput(stdout)
        except subprocess.CalledProcessError as e:
            return StringToolOutput(f"Validation Failed. Details:\n{e.output}")

class SendEmailTool:
    name = "SendEmail"
    description = "Send an email."

    def __init__(self):
        self.email = os.getenv("USER_EMAIL")

    def handler(self, input):
        argument = input.get("argument", "")
        try:
            sendmail_input = f"Subject:Data Validation\n{argument}\n"
            process = subprocess.Popen(['sendmail', '-t', self.email], stdin=subprocess.PIPE, text=True)
            process.communicate(sendmail_input)
            return StringToolOutput("Email sent successfully.")
        except Exception as e:
            return StringToolOutput(f"Validation Failed. Details:\n{str(e)}")

class FindWhatsRunningByPortsTool:
    name = "FindWhatsRunningByPorts"
    description = "Determine what applications are running on the system by looking at open listening ports. Disregard ports that are used by typical Linux system processes."

    def __init__(self):
        pass

    def handler(self, input):
        try:
            stdout = subprocess.check_output(['netstat', '-al'], text=True)
            return StringToolOutput(stdout)
        except subprocess.CalledProcessError as e:
            return StringToolOutput(f"Validation Failed. Details:\n{e.output}")
