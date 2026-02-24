"""
Process scanner for workload discovery.
Scans running processes and matches them against application signatures.
"""

import re
from typing import Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from ...models import ApplicationInstance, ApplicationCategory, DetectionMethod, ConfidenceLevel, NetworkBinding
from .signatures import ApplicationSignature, get_signature_database


@dataclass
class ProcessInfo:
    """Information about a running process."""
    pid: int
    user: str
    command: str
    full_command: str


class ProcessScanner:
    """
    Scans running processes to detect applications.
    Uses process command lines and matches against signature database.
    """
    
    def __init__(self):
        """Initialize the process scanner."""
        self.signature_db = get_signature_database()
    
    def scan(self, ssh_exec: Callable[[str], Tuple[str, str, int]]) -> List[ApplicationInstance]:
        """
        Scan running processes and detect applications.
        
        Args:
            ssh_exec: Function to execute SSH commands, returns (stdout, stderr, exit_code)
            
        Returns:
            List of detected application instances
        """
        # Get process list
        processes = self._get_process_list(ssh_exec)
        
        if not processes:
            return []
        
        # Match processes against signatures
        detected_apps = self._match_processes(processes, ssh_exec)
        
        return detected_apps
    
    def _get_process_list(self, ssh_exec: Callable[[str], Tuple[str, str, int]]) -> List[ProcessInfo]:
        """
        Get list of running processes.
        
        Args:
            ssh_exec: Function to execute SSH commands
            
        Returns:
            List of ProcessInfo objects
        """
        # Try different ps commands based on OS
        commands = [
            "ps -eo pid,user,args --no-headers",  # Linux
            "ps -eo pid,user,command",  # Alternative Linux
            "ps aux"  # BSD/macOS style
        ]
        
        processes = []
        
        for cmd in commands:
            stdout, stderr, exit_code = ssh_exec(cmd)
            
            if exit_code == 0 and stdout:
                processes = self._parse_ps_output(stdout)
                if processes:
                    break
        
        return processes
    
    def _parse_ps_output(self, output: str) -> List[ProcessInfo]:
        """
        Parse ps command output into ProcessInfo objects.
        
        Args:
            output: ps command output
            
        Returns:
            List of ProcessInfo objects
        """
        processes = []
        lines = output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('PID') or line.startswith('USER'):
                continue
            
            # Parse line: PID USER COMMAND
            parts = line.split(None, 2)
            if len(parts) < 3:
                continue
            
            try:
                pid = int(parts[0])
                user = parts[1]
                command = parts[2]
                
                # Extract just the command name for matching
                cmd_name = command.split()[0] if command else ""
                
                processes.append(ProcessInfo(
                    pid=pid,
                    user=user,
                    command=cmd_name,
                    full_command=command
                ))
            except (ValueError, IndexError):
                continue
        
        return processes
    
    def _match_processes(
        self, 
        processes: List[ProcessInfo],
        ssh_exec: Callable[[str], Tuple[str, str, int]]
    ) -> List[ApplicationInstance]:
        """
        Match processes against application signatures.
        
        Args:
            processes: List of running processes
            ssh_exec: Function to execute SSH commands
            
        Returns:
            List of detected application instances
        """
        detected: Dict[str, ApplicationInstance] = {}
        
        for process in processes:
            # Try to match against all signatures
            matches = self.signature_db.match_process(process.full_command)
            
            for signature in matches:
                app_key = f"{signature.name}_{process.user}"
                
                if app_key not in detected:
                    # Create new application instance
                    version = self._detect_version(signature, process, ssh_exec)
                    
                    app_instance = ApplicationInstance(
                        name=signature.name,
                        category=signature.category,
                        version=version or "unknown",
                        vendor=signature.vendor,
                        detection_methods=[DetectionMethod.PROCESS_SCAN],
                        confidence=self._calculate_confidence(signature, process, version),
                        process_info={
                            'pid': process.pid,
                            'user': process.user,
                            'command': process.full_command
                        },
                        network_bindings=[],
                        config_files=[],
                        install_path=self._extract_install_path(process.full_command)
                    )
                    
                    detected[app_key] = app_instance
                else:
                    # Update existing instance with additional process info
                    existing = detected[app_key]
                    if 'additional_processes' not in existing.process_info:
                        existing.process_info['additional_processes'] = []
                    existing.process_info['additional_processes'].append({
                        'pid': process.pid,
                        'command': process.full_command
                    })
        
        return list(detected.values())
    
    def _detect_version(
        self,
        signature: ApplicationSignature,
        process: ProcessInfo,
        ssh_exec: Callable[[str], Tuple[str, str, int]]
    ) -> Optional[str]:
        """
        Detect application version.
        
        Args:
            signature: Application signature
            process: Process information
            ssh_exec: Function to execute SSH commands
            
        Returns:
            Detected version string or None
        """
        # First try to extract version from process command
        version = self.signature_db.extract_version(signature, process.full_command)
        if version:
            return version
        
        # Try version commands from signature
        for cmd in signature.version_commands:
            try:
                stdout, stderr, exit_code = ssh_exec(cmd)
                
                if exit_code == 0:
                    # Try to extract version from output
                    version = self.signature_db.extract_version(signature, stdout)
                    if version:
                        return version
                    
                    # Also try stderr (some apps output version to stderr)
                    version = self.signature_db.extract_version(signature, stderr)
                    if version:
                        return version
            except Exception:
                continue
        
        return None
    
    def _calculate_confidence(
        self,
        signature: ApplicationSignature,
        process: ProcessInfo,
        version: Optional[str]
    ) -> ConfidenceLevel:
        """
        Calculate confidence level for detected application.
        
        Args:
            signature: Application signature
            process: Process information
            version: Detected version (if any)
            
        Returns:
            Confidence level
        """
        score = 0
        
        # Base score for process match
        score += 40
        
        # Bonus for version detection
        if version and version != "unknown":
            score += 30
        
        # Bonus for specific process patterns (not generic)
        for pattern in signature.compiled_process_patterns:
            if pattern.search(process.full_command):
                # Check if pattern is specific (contains specific app name)
                if len(pattern.pattern) > 10:  # Heuristic for specificity
                    score += 20
                    break
        
        # Bonus for running as expected user
        if process.user in ['oracle', 'postgres', 'mysql', 'mongodb', 'redis']:
            score += 10
        
        # Convert score to confidence level
        if score >= 80:
            return ConfidenceLevel.HIGH
        elif score >= 60:
            return ConfidenceLevel.MEDIUM
        elif score >= 40:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNCERTAIN
    
    def _extract_install_path(self, command: str) -> Optional[str]:
        """
        Extract installation path from process command.
        
        Args:
            command: Process command line
            
        Returns:
            Installation path or None
        """
        # Common installation path patterns
        patterns = [
            r'(/opt/[^/\s]+)',
            r'(/usr/local/[^/\s]+)',
            r'(/usr/lib/[^/\s]+)',
            r'(/var/lib/[^/\s]+)',
            r'(/home/[^/]+/[^/\s]+)',
            r'(/u\d+/[^/\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, command)
            if match:
                return match.group(1)
        
        return None
    
    def get_process_tree(
        self,
        ssh_exec: Callable[[str], Tuple[str, str, int]],
        parent_pid: Optional[int] = None
    ) -> Dict[int, List[int]]:
        """
        Get process tree (parent-child relationships).
        
        Args:
            ssh_exec: Function to execute SSH commands
            parent_pid: Optional parent PID to filter by
            
        Returns:
            Dictionary mapping parent PID to list of child PIDs
        """
        stdout, stderr, exit_code = ssh_exec("ps -eo pid,ppid --no-headers")
        
        if exit_code != 0:
            return {}
        
        tree: Dict[int, List[int]] = {}
        
        for line in stdout.strip().split('\n'):
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    pid = int(parts[0])
                    ppid = int(parts[1])
                    
                    if ppid not in tree:
                        tree[ppid] = []
                    tree[ppid].append(pid)
                except ValueError:
                    continue
        
        return tree

# Made with Bob
