//
// Copyright contributors to the agentic-ai-cyberres project
//
import { DynamicTool, StringToolOutput } from "beeai-framework/tools/base";
import { z } from "zod";
import { ObjectId } from "mongodb";
import * as mongoDB from "mongodb";
import { execSync } from 'child_process';
import { getEnv, parseEnv } from "bee-agent-framework/internals/env";

/*
 * Tool to look at running processs to determine what applications may be running
 */
export const FindRunningProcessesTool = new DynamicTool({
  name: "FindRunningProcesses",
  description: "Determine what applications are running on the system by looking at running processesu. Disregard processes that are used by typical Linux system processes",
  inputSchema: z.object({
    argument: z.string()
  }),
  async handler(input) {

	var returnString = new String;
	var stdout = new String;

	// do shell escape to run ps to see what processes are running.  Exclude kernel processes.
	try {
		stdout = execSync('ps  --ppid 2 -p 2 --deselect').toString();
		console.log(`stdout: ${stdout}`);
		returnString = stdout;
	} catch (error: any) {
		console.error(`Error: ${error.message}`);
		if (error.stderr) {
			console.error(`stderr: ${error.stderr.toString()}`);
  		}
		returnString = "Validation Failed.  Details:\n" + error.stderr;
	}

    	return new StringToolOutput(returnString);

  },
});

/*
 * Tool to validate mongoDB databases
 */
export const MongoDBDataValidatorTool = new DynamicTool({
  name: "MongoDBDataValidator",
  description: "This tool validates a mongod database to ensure the database is not corrupted. Do not use this tool to validate anything that is not mongod. It can only be used if mongod is currently running.",
  inputSchema: z.object({
    argument: z.string()
  }),
  async handler(input) {

	var returnString = new String;
	var stdout = new String;
	let workloadToValidate: string = "mongod";

	console.log(`argument: `+ input.argument);
	// if argument is not mongod, then agent is trying to use this tool to validate another workload.  Don't let it.
	if (input.argument !== workloadToValidate) {
		console.log(input.argument + ` is not a mongod workload. This tool cannot be used to validate ` + input.argument);
		returnString = "Validation Failed. Reason: " + input.argument + " cannot be used to validate " + workloadToValidate;
	} else {
		console.log(`Validating mongod workload: `+ input.argument);

		// do shell escape to run mongodb commands through mongosh
		try {
			stdout = execSync('mongosh --file src/helpers/mongoDBDataValidator.js').toString();
			console.log(`stdout: ${stdout}`);
			returnString = stdout;
		} catch (error: any) {
			console.error(`Error: ${error.message}`);
			if (error.status) {
				console.error(`Validation failed.`);
			}
			if (error.stderr) {
				console.error(`stderr: ${error.stderr.toString()}`);
  			}
			returnString = "Validation Failed.  Details:\n" + error.stderr;
		}
	}
    	return new StringToolOutput(returnString);
  },
});

/*
 * Tool to send email.
 * Initially intended for emailing results when agent runs autonomously
 */
export const SendEmailTool = new DynamicTool({
  name: "SendEmail",
  description: "Send an email.",
  inputSchema: z.object({
    argument: z.string()
  }),
  async handler(input) {

	var returnString = new String;
	var stdout = new String;
	var email = getEnv("USER_EMAIL");

	// do shell escape to run sendmail to send an email. (for sharing results when agent is run autonomously.))
	try {
		stdout = execSync('set -x; sendmail -t ' + email + ' << EOM\nSubject:Data Validation\n' + input.argument + '\nEOM').toString();
		console.log(`stdout: ${stdout}`);
		returnString = stdout;
	} catch (error: any) {
		console.error(`Error: ${error.message}`);
		if (error.stderr) {
			console.error(`stderr: ${error.stderr.toString()}`);
  		}
		returnString = "Validation Failed.  Details:\n" + error.stderr;
	}

    	return new StringToolOutput(returnString);

  },
});

/*
 * Tool to look at listening ports to determine what applications may be running
 */
export const FindWhatsRunningByPortsTool = new DynamicTool({
  name: "FindWhatsRunningByPorts",
  description: "Determine what applications are running on the system by looking at open listening ports.  Disregard ports that are used by typical Linux system processes.",
  inputSchema: z.object({
    min: z.number().int().min(0),
    max: z.number().int(),
  }),
  async handler(input) {

	var returnString = new String;
	var stdout = new String;

	// do shell escape to run netstat to see what ports are listening
	try {
		stdout = execSync('netstat -al').toString();
		console.log(`stdout: ${stdout}`);
		returnString = stdout;
	} catch (error: any) {
		console.error(`Error: ${error.message}`);
		if (error.stderr) {
			console.error(`stderr: ${error.stderr.toString()}`);
  		}
		returnString = "Validation Failed.  Details:\n" + error.stderr;
	}

    	return new StringToolOutput(returnString);

  },
});

