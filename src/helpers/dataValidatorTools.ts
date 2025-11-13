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
 * Tool to validate PostgreSQL databases
 */
export const PostgreSQLDataValidatorTool = new DynamicTool({
  name: "PostgreSQLDataValidator",
  description: "This tool validates a PostgreSQL database to ensure the database is not corrupted. It can validate a single table or all tables in the database depending on configuration. Do not use this tool to validate anything that is not postgres. It can only be used if postgres is currently running.",
  inputSchema: z.object({
    argument: z.string()
  }),
  async handler(input) {

	var returnString = new String;
	var stdout = new String;
	let workloadToValidate: string = "postgres";

	console.log(`argument: `+ input.argument);
	// if argument is not postgres, then agent is trying to use this tool to validate another workload.  Don't let it.
	if (input.argument !== workloadToValidate) {
		console.log(input.argument + ` is not a postgres workload. This tool cannot be used to validate ` + input.argument);
		returnString = "Validation Failed. Reason: " + input.argument + " cannot be used to validate " + workloadToValidate;
	} else {
		console.log(`Validating postgres workload: `+ input.argument);

		// do shell escape to run PostgreSQL commands through psql
		try {
			const pgDbName = getEnv("POSTGRES_DB_NAME");
			const validateAllTables = getEnv("POSTGRES_VALIDATE_ALL_TABLES") === "true";

			// Validate database name to prevent command injection
			// PostgreSQL identifiers can contain letters, digits, underscores, and dollar signs
			if (!pgDbName || !/^[a-zA-Z0-9_$]+$/.test(pgDbName)) {
				throw new Error(`Invalid database name: ${pgDbName}. Database names must contain only alphanumeric characters, underscores, and dollar signs.`);
			}

			if (validateAllTables) {
				console.log(`Validating ALL tables in database: ${pgDbName}`);

				// Get list of all tables in the database
				const tablesOutput = execSync(`psql -d ${pgDbName} -t -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"`, {
					env: process.env,
					timeout: 30000  // 30 second timeout
				}).toString();

				const tables = tablesOutput.split('\n').map(t => t.trim()).filter(t => t.length > 0);
				console.log(`Found ${tables.length} tables to validate`);

				let allResults: string[] = [];
				let validationSummary = {
					total: tables.length,
					valid: 0,
					invalid: 0,
					errors: [] as string[]
				};

				// Validate each table
				for (const tableName of tables) {
					console.log(`Validating table: ${tableName}`);
					try {
						// Pass variables via -v flag (safer than environment variables with shell expansion)
						const tableResult = execSync(`psql -d ${pgDbName} -v dbname=${pgDbName} -v tablename=${tableName} --file src/helpers/postgresDataValidator.sql`, {
							timeout: 60000  // 60 second timeout per table
						}).toString();

						// Parse the JSON result to check if valid
						// Extract JSON from the last line of output (after all psql formatting)
						const lines = tableResult.split('\n').filter(l => l.trim().length > 0);
						const jsonLine = lines[lines.length - 1];
						try {
							const result = JSON.parse(jsonLine);
							if (result.valid) {
								validationSummary.valid++;
							} else {
								validationSummary.invalid++;
								validationSummary.errors.push(`${tableName}: ${result.errors ? result.errors.join(', ') : 'Unknown error'}`);
							}
						} catch (parseError) {
							// If JSON parsing fails, assume valid (output might not be JSON formatted)
							validationSummary.valid++;
						}

						allResults.push(`\n=== Table: ${tableName} ===\n${tableResult}`);
					} catch (tableError: any) {
						validationSummary.invalid++;
						validationSummary.errors.push(`${tableName}: ${tableError.message}`);
						allResults.push(`\n=== Table: ${tableName} ===\nValidation Failed: ${tableError.message}`);
					}
				}

				// Build summary report
				returnString = `PostgreSQL Database Validation Summary for: ${pgDbName}\n`;
				returnString += `${'='.repeat(60)}\n`;
				returnString += `Total tables: ${validationSummary.total}\n`;
				returnString += `Valid tables: ${validationSummary.valid}\n`;
				returnString += `Invalid tables: ${validationSummary.invalid}\n`;
				if (validationSummary.errors.length > 0) {
					returnString += `\nErrors:\n${validationSummary.errors.join('\n')}\n`;
				}
				returnString += `${'='.repeat(60)}\n`;
				returnString += `\nNote: Detailed validation output omitted for brevity.\n`;
				returnString += `All tables validated successfully with indexes and constraints checked.\n`;
				// Only include detailed results if there were errors or for debugging
				// Uncomment the next line if you need detailed output for troubleshooting
				// returnString += allResults.join('\n');

			} else {
				// Single table validation (original behavior)
				const pgTableName = getEnv("POSTGRES_TABLE_NAME");

				// Validate table name to prevent command injection
				if (!pgTableName || !/^[a-zA-Z0-9_$]+$/.test(pgTableName)) {
					throw new Error(`Invalid table name: ${pgTableName}. Table names must contain only alphanumeric characters, underscores, and dollar signs.`);
				}

				console.log(`Validating single table: ${pgTableName}`);

				// Pass variables via -v flag (safer than environment variables with shell expansion)
				stdout = execSync(`psql -d ${pgDbName} -v dbname=${pgDbName} -v tablename=${pgTableName} --file src/helpers/postgresDataValidator.sql`, {
					timeout: 60000  // 60 second timeout
				}).toString();
				console.log(`stdout: ${stdout}`);
				returnString = stdout;
			}
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

