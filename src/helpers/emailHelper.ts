//
// Copyright contributors to the agentic-ai-cyberres project
//
import { execSync } from 'child_process';
import { getEnv } from "beeai-framework/internals/env";

/**
 * Interface for email options
 */
export interface EmailOptions {
  to?: string;           // Recipient email address (optional, defaults to USER_EMAIL env var)
  subject?: string;      // Email subject (optional, defaults to "Data Validation")
  body: string;          // Email body content (required)
  from?: string;         // Sender email address (optional)
}

/**
 * Interface for email result
 */
export interface EmailResult {
  success: boolean;
  message: string;
  error?: string;
}

/**
 * Send an email using the sendmail command
 * 
 * @param options - Email configuration options
 * @returns EmailResult object with success status and message
 * 
 * @example
 * ```typescript
 * const result = await sendEmail({
 *   to: "user@example.com",
 *   subject: "Validation Results",
 *   body: "All validations passed successfully."
 * });
 * 
 * if (result.success) {
 *   console.log("Email sent successfully");
 * } else {
 *   console.error("Failed to send email:", result.error);
 * }
 * ```
 */
export async function sendEmail(options: EmailOptions): Promise<EmailResult> {
  try {
    // Get recipient email from options or environment variable
    const recipientEmail = options.to || getEnv("USER_EMAIL");
    
    if (!recipientEmail) {
      return {
        success: false,
        message: "Failed to send email",
        error: "No recipient email address provided. Set USER_EMAIL environment variable or provide 'to' option."
      };
    }

    // Validate email format (basic validation)
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(recipientEmail)) {
      return {
        success: false,
        message: "Failed to send email",
        error: `Invalid email address format: ${recipientEmail}`
      };
    }

    // Set default subject if not provided
    const subject = options.subject || "Data Validation";
    
    // Escape special characters in body to prevent command injection
    // const sanitizedBody = options.body.replace(/'/g, "'\\''");
    
    // Build the email message
    let emailMessage = `Subject: ${subject}\n`;
    
    if (options.from) {
      emailMessage += `From: ${options.from}\n`;
    }
    
    emailMessage += `\n${options.body}`;

    // Escape special characters in the complete message to prevent command injection
    const sanitizedMessage = emailMessage.replace(/'/g, "'\\''");
    
    // Execute sendmail command
    // Using echo with pipe to avoid shell injection issues
    const command = `echo '${sanitizedMessage}' | sendmail -t ${recipientEmail}`;
    //const command = `echo '${sanitizedBody}' | sendmail -t ${recipientEmail}`;
    
    console.log(`Sending email to: ${recipientEmail}`);
    console.log(`Subject: ${subject}`);
    
    const stdout = execSync(command, {
      encoding: 'utf-8',
      timeout: 10000  // 10 second timeout
    });
    
    // if sendmail success there wont' be any output, but print the output for possible debugging 
    console.log(`Email sent successfully.  ${stdout}`);
    
    return {
      success: true,
      message: `Email sent successfully to ${recipientEmail}`
    };
    
  } catch (error: any) {
    console.error(`Error sending email: ${error.message}`);
    
    let errorDetails = error.message;
    if (error.stderr) {
      errorDetails += `\nStderr: ${error.stderr.toString()}`;
      console.error(`stderr: ${error.stderr.toString()}`);
    }
    
    return {
      success: false,
      message: "Failed to send email",
      error: errorDetails
    };
  }
}

/**
 * Send a simple text email with minimal configuration
 * 
 * @param body - The email body content
 * @param subject - Optional subject line (defaults to "Data Validation")
 * @returns EmailResult object with success status and message
 * 
 * @example
 * ```typescript
 * const result = await sendSimpleEmail("Validation completed successfully!");
 * ```
 */
export async function sendSimpleEmail(body: string, subject?: string): Promise<EmailResult> {
  return sendEmail({ body, subject });
}

// Made with Bob

