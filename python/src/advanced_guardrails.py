#!/usr/bin/env python3
#
# Copyright contributors to the agentic-ai-cyberres project
#
"""
Advanced Guardrails System
Provides additional security layers including rate limiting, content filtering, and behavioral analysis.
"""

import time
import hashlib
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from input_guardrails import GuardrailViolation, GuardrailViolationType, GuardrailSeverity

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests_per_minute: int = 10
    max_requests_per_hour: int = 100
    max_requests_per_day: int = 1000
    cooldown_period_seconds: int = 60


@dataclass
class RequestMetrics:
    """Metrics for tracking requests."""
    total_requests: int = 0
    blocked_requests: int = 0
    violations_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_request_time: Optional[datetime] = None
    request_timestamps: List[datetime] = field(default_factory=list)


class RateLimiter:
    """Rate limiting to prevent abuse."""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self.metrics = RequestMetrics()
        self.blocked_until: Optional[datetime] = None
    
    def check_rate_limit(self, user_id: str = "default") -> tuple[bool, Optional[str]]:
        """Check if request is within rate limits.
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (is_allowed, reason if blocked)
        """
        now = datetime.now()
        
        # Check if in cooldown period
        if self.blocked_until and now < self.blocked_until:
            remaining = (self.blocked_until - now).seconds
            return False, f"Rate limit exceeded. Try again in {remaining} seconds"
        
        # Clean old timestamps
        cutoff_time = now - timedelta(days=1)
        self.metrics.request_timestamps = [
            ts for ts in self.metrics.request_timestamps
            if ts > cutoff_time
        ]
        
        # Check per-minute limit
        one_minute_ago = now - timedelta(minutes=1)
        recent_requests = sum(
            1 for ts in self.metrics.request_timestamps
            if ts > one_minute_ago
        )
        if recent_requests >= self.config.max_requests_per_minute:
            self.blocked_until = now + timedelta(seconds=self.config.cooldown_period_seconds)
            return False, f"Rate limit: {self.config.max_requests_per_minute} requests/minute exceeded"
        
        # Check per-hour limit
        one_hour_ago = now - timedelta(hours=1)
        hourly_requests = sum(
            1 for ts in self.metrics.request_timestamps
            if ts > one_hour_ago
        )
        if hourly_requests >= self.config.max_requests_per_hour:
            return False, f"Rate limit: {self.config.max_requests_per_hour} requests/hour exceeded"
        
        # Check per-day limit
        daily_requests = len(self.metrics.request_timestamps)
        if daily_requests >= self.config.max_requests_per_day:
            return False, f"Rate limit: {self.config.max_requests_per_day} requests/day exceeded"
        
        # Record request
        self.metrics.request_timestamps.append(now)
        self.metrics.total_requests += 1
        self.metrics.last_request_time = now
        
        return True, None


class ContentFilter:
    """Advanced content filtering."""
    
    # Profanity and inappropriate content patterns
    INAPPROPRIATE_PATTERNS = [
        r'\b(fuck|shit|damn|hell|ass|bitch)\b',
        r'\b(xxx|porn|sex|nude)\b',
    ]
    
    # Spam patterns
    SPAM_PATTERNS = [
        r'(click here|buy now|limited offer|act now)',
        r'(viagra|cialis|pharmacy)',
        r'(lottery|winner|prize|claim)',
    ]
    
    # Repeated characters (potential spam)
    REPEATED_CHAR_PATTERN = r'(.)\1{10,}'
    
    @classmethod
    def check_content(cls, text: str) -> List[GuardrailViolation]:
        """Check content for inappropriate material.
        
        Args:
            text: Text to check
            
        Returns:
            List of violations
        """
        violations = []
        text_lower = text.lower()
        
        # Check for inappropriate content
        import re
        for pattern in cls.INAPPROPRIATE_PATTERNS:
            if re.search(pattern, text_lower):
                violations.append(GuardrailViolation(
                    violation_type=GuardrailViolationType.SUSPICIOUS_PATTERN,
                    severity=GuardrailSeverity.MEDIUM,
                    message="Inappropriate content detected",
                    matched_pattern=pattern,
                    suggestion="Use professional language"
                ))
        
        # Check for spam patterns
        for pattern in cls.SPAM_PATTERNS:
            if re.search(pattern, text_lower):
                violations.append(GuardrailViolation(
                    violation_type=GuardrailViolationType.SUSPICIOUS_PATTERN,
                    severity=GuardrailSeverity.HIGH,
                    message="Spam-like content detected",
                    matched_pattern=pattern,
                    suggestion="Remove promotional content"
                ))
        
        # Check for repeated characters
        if re.search(cls.REPEATED_CHAR_PATTERN, text):
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.SUSPICIOUS_PATTERN,
                severity=GuardrailSeverity.MEDIUM,
                message="Excessive repeated characters detected",
                suggestion="Remove repeated characters"
            ))
        
        return violations


class BehavioralAnalyzer:
    """Analyze behavioral patterns to detect anomalies."""
    
    def __init__(self):
        """Initialize behavioral analyzer."""
        self.request_history: List[Dict] = []
        self.input_hashes: Set[str] = set()
        self.max_history = 100
    
    def analyze_request(self, text: str, user_id: str = "default") -> List[GuardrailViolation]:
        """Analyze request for behavioral anomalies.
        
        Args:
            text: Input text
            user_id: User identifier
            
        Returns:
            List of violations
        """
        violations = []
        
        # Check for duplicate requests (potential replay attack)
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        if text_hash in self.input_hashes:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.SUSPICIOUS_PATTERN,
                severity=GuardrailSeverity.LOW,
                message="Duplicate request detected",
                suggestion="This exact input was already processed"
            ))
        else:
            self.input_hashes.add(text_hash)
            # Keep only recent hashes
            if len(self.input_hashes) > self.max_history:
                self.input_hashes.pop()
        
        # Record request
        self.request_history.append({
            'timestamp': datetime.now(),
            'user_id': user_id,
            'text_hash': text_hash,
            'length': len(text)
        })
        
        # Keep history bounded
        if len(self.request_history) > self.max_history:
            self.request_history.pop(0)
        
        # Check for rapid-fire requests (potential automation)
        recent_requests = [
            r for r in self.request_history
            if (datetime.now() - r['timestamp']).seconds < 10
        ]
        if len(recent_requests) > 5:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.SUSPICIOUS_PATTERN,
                severity=GuardrailSeverity.MEDIUM,
                message="Unusually rapid requests detected",
                suggestion="Slow down request rate"
            ))
        
        return violations


class EncodingValidator:
    """Validate input encoding and detect obfuscation attempts."""
    
    @staticmethod
    def check_encoding(text: str) -> List[GuardrailViolation]:
        """Check for encoding issues and obfuscation.
        
        Args:
            text: Input text
            
        Returns:
            List of violations
        """
        violations = []
        
        # Check for excessive unicode characters
        non_ascii_count = sum(1 for c in text if ord(c) > 127)
        if non_ascii_count > len(text) * 0.3:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.SUSPICIOUS_PATTERN,
                severity=GuardrailSeverity.MEDIUM,
                message="Excessive non-ASCII characters detected",
                suggestion="Use standard ASCII characters when possible"
            ))
        
        # Check for null bytes (potential injection)
        if '\x00' in text:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.INJECTION_ATTEMPT,
                severity=GuardrailSeverity.CRITICAL,
                message="Null byte detected in input",
                suggestion="Remove null bytes from input"
            ))
        
        # Check for control characters
        control_chars = sum(1 for c in text if ord(c) < 32 and c not in '\n\r\t')
        if control_chars > 0:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.SUSPICIOUS_PATTERN,
                severity=GuardrailSeverity.HIGH,
                message="Control characters detected in input",
                suggestion="Remove control characters"
            ))
        
        return violations


class AdvancedGuardrails:
    """Advanced guardrails system with multiple security layers."""
    
    def __init__(
        self,
        enable_rate_limiting: bool = True,
        enable_content_filter: bool = True,
        enable_behavioral_analysis: bool = True,
        enable_encoding_validation: bool = True,
        rate_limit_config: Optional[RateLimitConfig] = None
    ):
        """Initialize advanced guardrails.
        
        Args:
            enable_rate_limiting: Enable rate limiting
            enable_content_filter: Enable content filtering
            enable_behavioral_analysis: Enable behavioral analysis
            enable_encoding_validation: Enable encoding validation
            rate_limit_config: Rate limit configuration
        """
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_content_filter = enable_content_filter
        self.enable_behavioral_analysis = enable_behavioral_analysis
        self.enable_encoding_validation = enable_encoding_validation
        
        self.rate_limiter = RateLimiter(rate_limit_config) if enable_rate_limiting else None
        self.content_filter = ContentFilter() if enable_content_filter else None
        self.behavioral_analyzer = BehavioralAnalyzer() if enable_behavioral_analysis else None
        self.encoding_validator = EncodingValidator() if enable_encoding_validation else None
    
    def validate(
        self,
        text: str,
        user_id: str = "default"
    ) -> tuple[bool, List[GuardrailViolation], Optional[str]]:
        """Run all advanced validations.
        
        Args:
            text: Input text to validate
            user_id: User identifier
            
        Returns:
            Tuple of (is_valid, violations, rate_limit_message)
        """
        violations = []
        rate_limit_message = None
        
        # Check rate limiting first
        if self.enable_rate_limiting and self.rate_limiter:
            is_allowed, reason = self.rate_limiter.check_rate_limit(user_id)
            if not is_allowed:
                return False, [], reason
        
        # Run content filter
        if self.enable_content_filter and self.content_filter:
            violations.extend(self.content_filter.check_content(text))
        
        # Run behavioral analysis
        if self.enable_behavioral_analysis and self.behavioral_analyzer:
            violations.extend(self.behavioral_analyzer.analyze_request(text, user_id))
        
        # Run encoding validation
        if self.enable_encoding_validation and self.encoding_validator:
            violations.extend(self.encoding_validator.check_encoding(text))
        
        # Determine if valid (block on CRITICAL or HIGH)
        is_valid = not any(
            v.severity in [GuardrailSeverity.CRITICAL, GuardrailSeverity.HIGH]
            for v in violations
        )
        
        return is_valid, violations, rate_limit_message
    
    def get_metrics(self) -> Dict:
        """Get guardrails metrics.
        
        Returns:
            Dictionary of metrics
        """
        metrics = {}
        
        if self.rate_limiter:
            metrics['rate_limiter'] = {
                'total_requests': self.rate_limiter.metrics.total_requests,
                'blocked_requests': self.rate_limiter.metrics.blocked_requests,
                'last_request': self.rate_limiter.metrics.last_request_time.isoformat()
                if self.rate_limiter.metrics.last_request_time else None
            }
        
        if self.behavioral_analyzer:
            metrics['behavioral'] = {
                'history_size': len(self.behavioral_analyzer.request_history),
                'unique_inputs': len(self.behavioral_analyzer.input_hashes)
            }
        
        return metrics


# Made with Bob