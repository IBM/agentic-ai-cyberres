"""
Application signature database for workload discovery.
Loads and manages application signatures for detection.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass

from ...models import ApplicationCategory


@dataclass
class ApplicationSignature:
    """Represents an application signature for detection."""
    
    name: str
    category: ApplicationCategory
    vendor: str
    process_patterns: List[str]
    port_patterns: List[int]
    config_paths: List[str]
    version_commands: List[str]
    version_patterns: List[str]
    
    def __post_init__(self):
        """Compile regex patterns for efficient matching."""
        self.compiled_process_patterns = [
            re.compile(pattern) for pattern in self.process_patterns
        ]
        self.compiled_version_patterns = [
            re.compile(pattern) for pattern in self.version_patterns
        ]


class SignatureDatabase:
    """
    Manages application signatures for workload discovery.
    Provides efficient lookup and matching capabilities.
    """
    
    def __init__(self, signatures_path: Optional[Path] = None):
        """
        Initialize the signature database.
        
        Args:
            signatures_path: Path to signatures JSON file. If None, uses default.
        """
        self.signatures: Dict[str, ApplicationSignature] = {}
        self.process_index: Dict[str, Set[str]] = {}  # pattern -> app names
        self.port_index: Dict[int, Set[str]] = {}  # port -> app names
        self.category_index: Dict[ApplicationCategory, Set[str]] = {}  # category -> app names
        
        if signatures_path is None:
            # Use default path relative to this file
            signatures_path = Path(__file__).parent.parent.parent / "resources" / "signatures" / "applications.json"
        
        self.signatures_path = signatures_path
        self._load_signatures()
    
    def _load_signatures(self) -> None:
        """Load signatures from JSON file and build indexes."""
        if not self.signatures_path.exists():
            raise FileNotFoundError(f"Signatures file not found: {self.signatures_path}")
        
        with open(self.signatures_path, 'r') as f:
            data = json.load(f)
        
        for app_data in data.get('applications', []):
            try:
                # Convert category string to enum
                category_str = app_data['category']
                category = ApplicationCategory(category_str)
                
                signature = ApplicationSignature(
                    name=app_data['name'],
                    category=category,
                    vendor=app_data['vendor'],
                    process_patterns=app_data['process_patterns'],
                    port_patterns=app_data['port_patterns'],
                    config_paths=app_data['config_paths'],
                    version_commands=app_data['version_commands'],
                    version_patterns=app_data['version_patterns']
                )
                
                self.signatures[signature.name] = signature
                
                # Build indexes for efficient lookup
                self._index_signature(signature)
                
            except (KeyError, ValueError) as e:
                print(f"Warning: Failed to load signature for {app_data.get('name', 'unknown')}: {e}")
                continue
    
    def _index_signature(self, signature: ApplicationSignature) -> None:
        """Build indexes for efficient signature lookup."""
        app_name = signature.name
        
        # Index by process patterns
        for pattern in signature.process_patterns:
            if pattern not in self.process_index:
                self.process_index[pattern] = set()
            self.process_index[pattern].add(app_name)
        
        # Index by ports
        for port in signature.port_patterns:
            if port not in self.port_index:
                self.port_index[port] = set()
            self.port_index[port].add(app_name)
        
        # Index by category
        if signature.category not in self.category_index:
            self.category_index[signature.category] = set()
        self.category_index[signature.category].add(app_name)
    
    def get_signature(self, app_name: str) -> Optional[ApplicationSignature]:
        """Get signature by application name."""
        return self.signatures.get(app_name)
    
    def get_all_signatures(self) -> List[ApplicationSignature]:
        """Get all loaded signatures."""
        return list(self.signatures.values())
    
    def get_signatures_by_category(self, category: ApplicationCategory) -> List[ApplicationSignature]:
        """Get all signatures for a specific category."""
        app_names = self.category_index.get(category, set())
        return [self.signatures[name] for name in app_names]
    
    def match_process(self, process_cmd: str) -> List[ApplicationSignature]:
        """
        Match a process command line against all signatures.
        
        Args:
            process_cmd: Process command line string
            
        Returns:
            List of matching application signatures
        """
        matches = []
        
        for signature in self.signatures.values():
            for pattern in signature.compiled_process_patterns:
                if pattern.search(process_cmd):
                    matches.append(signature)
                    break  # Only add once per signature
        
        return matches
    
    def match_port(self, port: int) -> List[ApplicationSignature]:
        """
        Match a port number against all signatures.
        
        Args:
            port: Port number
            
        Returns:
            List of matching application signatures
        """
        app_names = self.port_index.get(port, set())
        return [self.signatures[name] for name in app_names]
    
    def extract_version(self, signature: ApplicationSignature, text: str) -> Optional[str]:
        """
        Extract version from text using signature's version patterns.
        
        Args:
            signature: Application signature
            text: Text to extract version from
            
        Returns:
            Extracted version string or None
        """
        for pattern in signature.compiled_version_patterns:
            match = pattern.search(text)
            if match:
                # Return first captured group or full match
                return match.group(1) if match.groups() else match.group(0)
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded signatures."""
        category_counts = {}
        for category, app_names in self.category_index.items():
            category_counts[category.value] = len(app_names)
        
        return {
            'total_applications': len(self.signatures),
            'total_process_patterns': len(self.process_index),
            'total_ports': len(self.port_index),
            'by_category': category_counts
        }
    
    def validate_signatures(self) -> List[str]:
        """
        Validate all signatures for completeness and correctness.
        
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        for name, signature in self.signatures.items():
            # Check for empty lists
            if not signature.process_patterns:
                issues.append(f"{name}: No process patterns defined")
            
            if not signature.port_patterns:
                issues.append(f"{name}: No port patterns defined")
            
            # Check regex compilation
            for i, pattern in enumerate(signature.process_patterns):
                try:
                    re.compile(pattern)
                except re.error as e:
                    issues.append(f"{name}: Invalid process pattern {i}: {pattern} - {e}")
            
            for i, pattern in enumerate(signature.version_patterns):
                try:
                    re.compile(pattern)
                except re.error as e:
                    issues.append(f"{name}: Invalid version pattern {i}: {pattern} - {e}")
        
        return issues


# Global singleton instance
_signature_db: Optional[SignatureDatabase] = None


def get_signature_database() -> SignatureDatabase:
    """
    Get the global signature database instance.
    Creates it on first call (lazy initialization).
    """
    global _signature_db
    if _signature_db is None:
        _signature_db = SignatureDatabase()
    return _signature_db


def reload_signature_database(signatures_path: Optional[Path] = None) -> SignatureDatabase:
    """
    Reload the signature database from file.
    Useful for testing or when signatures are updated.
    """
    global _signature_db
    _signature_db = SignatureDatabase(signatures_path)
    return _signature_db

# Made with Bob
