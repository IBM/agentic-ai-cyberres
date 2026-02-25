#!/usr/bin/env python3
#
# Copyright contributors to the agentic-ai-cyberres project
#
"""
Input Guardrails System for Python Agent
Provides multi-layered security validation for user inputs.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class GuardrailViolationType(Enum):
    """Types of guardrail violations."""
    PII_DETECTED = "pii_detected"
    MALICIOUS_COMMAND = "malicious_command"
    OUT_OF_CONTEXT = "out_of_context"
    EXCESSIVE_LENGTH = "excessive_length"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    INJECTION_ATTEMPT = "injection_attempt"
    CREDENTIAL_EXPOSURE = "credential_exposure"


class GuardrailSeverity(Enum):
    """Severity levels for guardrail violations."""
    CRITICAL = "critical"  # Block immediately
    HIGH = "high"          # Block with detailed warning
    MEDIUM = "medium"      # Warn but allow
    LOW = "low"            # Log only


@dataclass
class GuardrailViolation:
    """Represents a guardrail violation."""
    violation_type: GuardrailViolationType
    severity: GuardrailSeverity
    message: str
    matched_pattern: Optional[str] = None
    suggestion: Optional[str] = None


class PIIDetector:
    """Detects Personally Identifiable Information (PII) in input."""
    
    # PII patterns (IP addresses removed - they're needed for infrastructure validation)
    # Updated for Indian formats
    PATTERNS = {
        'aadhaar': (
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            "Aadhaar number detected"
        ),
        'pan': (
            r'\b[A-Z]{5}\d{4}[A-Z]\b',
            "PAN card number detected"
        ),
        'credit_card': (
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            "Credit card number detected"
        ),
        'email': (
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "Email address detected"
        ),
        'phone': (
            r'\b(?:\+91[-.\s]?)?[6-9]\d{9}\b|\b(?:\+?91[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}\b',
            "Phone number detected"
        ),
        'passport': (
            r'\b[A-Z]\d{7}\b',
            "Indian passport number detected"
        ),
    }
    
    @classmethod
    def detect(cls, text: str) -> List[GuardrailViolation]:
        """Detect PII in text.
        
        Args:
            text: Input text to check
            
        Returns:
            List of violations found
        """
        violations = []
        
        for pii_type, (pattern, message) in cls.PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                violations.append(GuardrailViolation(
                    violation_type=GuardrailViolationType.PII_DETECTED,
                    severity=GuardrailSeverity.CRITICAL,
                    message=f"{message}: {pii_type}",
                    matched_pattern=matches[0] if matches else None,
                    suggestion=f"Remove or redact {pii_type} from input"
                ))
        
        return violations


class MaliciousCommandDetector:
    """Detects malicious commands and injection attempts."""
    
    # Dangerous command patterns
    DANGEROUS_COMMANDS = [
        # System destruction
        r'\brm\s+-rf\s+/',
        r'\bformat\s+[c-z]:',
        r'\bdel\s+/[fqs]\s+',
        r'\bmkfs\.',
        
        # Data exfiltration
        r'\bcurl\s+.*\|\s*bash',
        r'\bwget\s+.*\|\s*sh',
        r'\bnc\s+.*-e\s+/bin/',
        r'\b/dev/tcp/',
        
        # Privilege escalation
        r'\bsudo\s+su\s*-',
        r'\bchmod\s+777',
        r'\bchown\s+root',
        
        # Code injection
        r';\s*rm\s+-rf',
        r'\|\s*sh\s*$',
        r'`.*`',
        r'\$\(.*\)',
        
        # SQL injection patterns
        r"'\s*OR\s+'1'\s*=\s*'1",
        r";\s*DROP\s+TABLE",
        r"UNION\s+SELECT",
        r"--\s*$",
        
        # Command injection
        r'&&\s*rm\s+',
        r'\|\|\s*rm\s+',
        r'>\s*/dev/null\s*&&',
    ]
    
    # Destructive/negative action keywords
    DESTRUCTIVE_KEYWORDS = [
        'delete', 'remove', 'destroy', 'wipe', 'erase', 'purge',
        'shutdown', 'poweroff', 'halt', 'reboot', 'restart',
        'kill', 'terminate', 'stop', 'disable', 'uninstall',
        'drop', 'truncate', 'clear', 'flush', 'reset'
    ]
    
    # Suspicious keywords
    SUSPICIOUS_KEYWORDS = [
        'password', 'passwd', 'secret', 'token', 'api_key', 'apikey',
        'private_key', 'credential', 'auth', 'authorization'
    ]
    
    @classmethod
    def detect(cls, text: str) -> List[GuardrailViolation]:
        """Detect malicious commands in text.
        
        Args:
            text: Input text to check
            
        Returns:
            List of violations found
        """
        violations = []
        text_lower = text.lower()
        
        # Check for dangerous command patterns
        for pattern in cls.DANGEROUS_COMMANDS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(GuardrailViolation(
                    violation_type=GuardrailViolationType.MALICIOUS_COMMAND,
                    severity=GuardrailSeverity.CRITICAL,
                    message="Potentially malicious command detected",
                    matched_pattern=pattern,
                    suggestion="Remove dangerous commands from input"
                ))
        
        # Check for destructive/negative action keywords
        found_destructive = []
        for keyword in cls.DESTRUCTIVE_KEYWORDS:
            # Use word boundaries to avoid false positives
            if re.search(rf'\b{keyword}\b', text_lower):
                found_destructive.append(keyword)
        
        if found_destructive:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.MALICIOUS_COMMAND,
                severity=GuardrailSeverity.CRITICAL,
                message=f"Destructive action keywords detected: {', '.join(found_destructive)}",
                matched_pattern=', '.join(found_destructive),
                suggestion="This agent is for validation only. Destructive actions like delete, remove, shutdown are not allowed"
            ))
        
        # Check for credential exposure in plain text
        for keyword in cls.SUSPICIOUS_KEYWORDS:
            if keyword in text_lower:
                # Check if it's followed by a value (potential credential exposure)
                pattern = rf'{keyword}\s*[:=]\s*["\']?([^\s"\']+)'
                if re.search(pattern, text, re.IGNORECASE):
                    violations.append(GuardrailViolation(
                        violation_type=GuardrailViolationType.CREDENTIAL_EXPOSURE,
                        severity=GuardrailSeverity.HIGH,
                        message=f"Potential credential exposure: {keyword}",
                        matched_pattern=keyword,
                        suggestion="Use environment variables or secure credential storage"
                    ))
        
        return violations


class ContextValidator:
    """Validates that input is within expected context."""
    
    # Valid context keywords for infrastructure validation
    VALID_CONTEXTS = [
        'vm', 'virtual machine', 'server', 'host', 'instance',
        'database', 'db', 'oracle', 'mongodb', 'mongo', 'sql',
        'validate', 'check', 'verify', 'test', 'discover',
        'ssh', 'connection', 'port', 'service', 'process',
        'network', 'infrastructure', 'resource', 'workload',
        'recovery', 'backup', 'restore', 'cluster', 'node',
        'ip', 'address', 'hostname', 'recovered', 'at'
    ]
    
    # Out-of-context keywords
    OUT_OF_CONTEXT_KEYWORDS = [
        'weather', 'recipe', 'movie', 'game', 'music', 'sports',
        'celebrity', 'news', 'politics', 'shopping', 'travel',
        'joke', 'story', 'poem', 'song', 'book', 'art'
    ]
    
    @staticmethod
    def is_gibberish(text: str) -> bool:
        """Check if text appears to be gibberish.
        
        Args:
            text: Input text to check
            
        Returns:
            True if text appears to be gibberish
        """
        # Remove whitespace and convert to lowercase
        clean_text = text.strip().lower()
        
        # Too short to determine
        if len(clean_text) < 3:
            return False
        
        # Check for excessive consonants (no vowels in long sequences)
        import re
        words = clean_text.split()
        
        for word in words:
            if len(word) > 4:
                # Check if word has very few or no vowels
                vowels = len(re.findall(r'[aeiou]', word))
                consonants = len(re.findall(r'[bcdfghjklmnpqrstvwxyz]', word))
                
                # If word is mostly consonants (>80%) and has >5 chars, likely gibberish
                if consonants > 0 and vowels / (vowels + consonants) < 0.2 and len(word) > 5:
                    return True
        
        # Check for random character sequences (no recognizable words)
        if len(words) == 1 and len(clean_text) > 5:
            # Single "word" with no spaces - check if it's all random
            has_vowels = bool(re.search(r'[aeiou]', clean_text))
            has_consonants = bool(re.search(r'[bcdfghjklmnpqrstvwxyz]', clean_text))
            has_numbers = bool(re.search(r'\d', clean_text))
            
            # If it's just random letters with poor vowel distribution
            if has_consonants and not has_numbers:
                vowel_count = len(re.findall(r'[aeiou]', clean_text))
                total_letters = len(re.findall(r'[a-z]', clean_text))
                if total_letters > 0 and vowel_count / total_letters < 0.15:
                    return True
        
        return False
    
    @classmethod
    def validate(cls, text: str) -> List[GuardrailViolation]:
        """Validate input context.
        
        Args:
            text: Input text to check
            
        Returns:
            List of violations found
        """
        violations = []
        text_lower = text.lower()
        
        # Check for gibberish first
        if cls.is_gibberish(text):
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.OUT_OF_CONTEXT,
                severity=GuardrailSeverity.HIGH,
                message="Input appears to be gibberish or nonsensical",
                suggestion="Please provide a clear request about infrastructure validation (e.g., 'Validate VM at 192.168.1.100')"
            ))
            return violations  # Return early for gibberish
        
        # Check for out-of-context keywords
        found_out_of_context = [
            keyword for keyword in cls.OUT_OF_CONTEXT_KEYWORDS
            if keyword in text_lower
        ]
        
        if found_out_of_context:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.OUT_OF_CONTEXT,
                severity=GuardrailSeverity.MEDIUM,
                message=f"Input appears out of context: {', '.join(found_out_of_context)}",
                matched_pattern=', '.join(found_out_of_context),
                suggestion="This agent is designed for infrastructure validation tasks"
            ))
        
        # Check if input has any valid context
        has_valid_context = any(
            keyword in text_lower for keyword in cls.VALID_CONTEXTS
        )
        
        if not has_valid_context and len(text.split()) > 2:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.OUT_OF_CONTEXT,
                severity=GuardrailSeverity.MEDIUM,
                message="Input may not be related to infrastructure validation",
                suggestion="Provide information about VMs, databases, or infrastructure resources (e.g., 'I recovered a VM at 192.168.1.100')"
            ))
        
        return violations


class InputGuardrails:
    """Main guardrails system for input validation."""
    
    MAX_INPUT_LENGTH = 5000
    MAX_PROMPT_LENGTH = 10000
    
    def __init__(self, strict_mode: bool = True):
        """Initialize guardrails.
        
        Args:
            strict_mode: If True, block on HIGH and CRITICAL violations
        """
        self.strict_mode = strict_mode
        self.pii_detector = PIIDetector()
        self.malicious_detector = MaliciousCommandDetector()
        self.context_validator = ContextValidator()
    
    def validate_input(self, text: str, input_type: str = "prompt") -> Tuple[bool, List[GuardrailViolation]]:
        """Validate input text against all guardrails.
        
        Args:
            text: Input text to validate
            input_type: Type of input (prompt, command, etc.)
            
        Returns:
            Tuple of (is_valid, list of violations)
        """
        violations = []
        
        # Check length
        max_length = self.MAX_PROMPT_LENGTH if input_type == "prompt" else self.MAX_INPUT_LENGTH
        if len(text) > max_length:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.EXCESSIVE_LENGTH,
                severity=GuardrailSeverity.HIGH,
                message=f"Input exceeds maximum length ({len(text)} > {max_length})",
                suggestion=f"Reduce input to under {max_length} characters"
            ))
        
        # Run all detectors
        violations.extend(self.pii_detector.detect(text))
        violations.extend(self.malicious_detector.detect(text))
        violations.extend(self.context_validator.validate(text))
        
        # Determine if input is valid
        if self.strict_mode:
            # Block on CRITICAL or HIGH severity
            is_valid = not any(
                v.severity in [GuardrailSeverity.CRITICAL, GuardrailSeverity.HIGH]
                for v in violations
            )
        else:
            # Only block on CRITICAL
            is_valid = not any(
                v.severity == GuardrailSeverity.CRITICAL
                for v in violations
            )
        
        return is_valid, violations
    
    def format_violations(self, violations: List[GuardrailViolation]) -> str:
        """Format violations for display.
        
        Args:
            violations: List of violations
            
        Returns:
            Formatted string
        """
        if not violations:
            return "✅ No violations detected"
        
        lines = ["⚠️  GUARDRAIL VIOLATIONS DETECTED:\n"]
        
        for i, violation in enumerate(violations, 1):
            severity_icon = {
                GuardrailSeverity.CRITICAL: "🚫",
                GuardrailSeverity.HIGH: "⛔",
                GuardrailSeverity.MEDIUM: "⚠️",
                GuardrailSeverity.LOW: "ℹ️"
            }[violation.severity]
            
            lines.append(f"{i}. {severity_icon} [{violation.severity.value.upper()}] {violation.message}")
            
            if violation.matched_pattern:
                lines.append(f"   Pattern: {violation.matched_pattern}")
            
            if violation.suggestion:
                lines.append(f"   💡 Suggestion: {violation.suggestion}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def validate_and_raise(self, text: str, input_type: str = "prompt") -> None:
        """Validate input and raise exception if invalid.
        
        Args:
            text: Input text to validate
            input_type: Type of input
            
        Raises:
            GuardrailViolationError: If validation fails
        """
        is_valid, violations = self.validate_input(text, input_type)
        
        if not is_valid:
            error_msg = self.format_violations(violations)
            logger.error(f"Guardrail validation failed:\n{error_msg}")
            raise GuardrailViolationError(error_msg, violations)
        
        # Log warnings for non-blocking violations
        warning_violations = [
            v for v in violations
            if v.severity in [GuardrailSeverity.MEDIUM, GuardrailSeverity.LOW]
        ]
        if warning_violations:
            warning_msg = self.format_violations(warning_violations)
            logger.warning(f"Guardrail warnings:\n{warning_msg}")


class GuardrailViolationError(Exception):
    """Exception raised when guardrail validation fails."""
    
    def __init__(self, message: str, violations: List[GuardrailViolation]):
        super().__init__(message)
        self.violations = violations


# Convenience function for quick validation
def validate_input(text: str, strict_mode: bool = True) -> Tuple[bool, List[GuardrailViolation]]:
    """Quick validation function.
    
    Args:
        text: Input text to validate
        strict_mode: If True, block on HIGH and CRITICAL violations
        
    Returns:
        Tuple of (is_valid, list of violations)
    """
    guardrails = InputGuardrails(strict_mode=strict_mode)
    return guardrails.validate_input(text)


# Made with Bob