"""
Port scanner for workload discovery.
Scans listening ports and matches them against application signatures.
"""

import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from ...models import ApplicationInstance, ApplicationCategory, DetectionMethod, ConfidenceLevel, NetworkBinding
from .signatures import ApplicationSignature, get_signature_database


@dataclass
class PortInfo:
    """Information about a listening port."""
    port: int
    protocol: str  # tcp, udp, tcp6, udp6
    address: str  # listening address (0.0.0.0, ::, specific IP)
    pid: Optional[int]
    process_name: Optional[str]
    user: Optional[str]


class PortScanner:
    """
    Scans listening ports to detect applications.
    Uses network port bindings and matches against signature database.
    """
    
    def __init__(self):
        """Initialize the port scanner."""
        self.signature_db = get_signature_database()
    
    def scan(self, ssh_exec: Callable[[str], Tuple[str, str, int]]) -> List[ApplicationInstance]:
        """
        Scan listening ports and detect applications.
        
        Args:
            ssh_exec: Function to execute SSH commands, returns (stdout, stderr, exit_code)
            
        Returns:
            List of detected application instances
        """
        # Get listening ports
        ports = self._get_listening_ports(ssh_exec)
        
        if not ports:
            return []
        
        # Match ports against signatures
        detected_apps = self._match_ports(ports, ssh_exec)
        
        return detected_apps
    
    def _get_listening_ports(self, ssh_exec: Callable[[str], Tuple[str, str, int]]) -> List[PortInfo]:
        """
        Get list of listening ports.
        
        Args:
            ssh_exec: Function to execute SSH commands
            
        Returns:
            List of PortInfo objects
        """
        # Try different commands based on availability
        commands = [
            "ss -tulpn",  # Modern Linux (iproute2)
            "netstat -tulpn",  # Traditional Linux
            "lsof -i -P -n | grep LISTEN"  # Alternative using lsof
        ]
        
        ports = []
        
        for cmd in commands:
            stdout, stderr, exit_code = ssh_exec(cmd)
            
            if exit_code == 0 and stdout:
                if 'ss' in cmd:
                    ports = self._parse_ss_output(stdout)
                elif 'netstat' in cmd:
                    ports = self._parse_netstat_output(stdout)
                elif 'lsof' in cmd:
                    ports = self._parse_lsof_output(stdout)
                
                if ports:
                    break
        
        return ports
    
    def _parse_ss_output(self, output: str) -> List[PortInfo]:
        """
        Parse 'ss -tulpn' output.
        
        Format: Netid State Recv-Q Send-Q Local Address:Port Peer Address:Port Process
        Example: tcp   LISTEN 0      128    0.0.0.0:22          0.0.0.0:*    users:(("sshd",pid=1234,fd=3))
        """
        ports = []
        lines = output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Netid') or line.startswith('State'):
                continue
            
            parts = line.split()
            if len(parts) < 5:
                continue
            
            try:
                protocol = parts[0].lower()  # tcp, udp, tcp6, udp6
                state = parts[1]
                
                if state != 'LISTEN' and state != 'UNCONN':  # UNCONN for UDP
                    continue
                
                # Parse local address:port
                local_addr = parts[4]
                if ':' in local_addr:
                    addr_parts = local_addr.rsplit(':', 1)
                    address = addr_parts[0]
                    port = int(addr_parts[1])
                else:
                    continue
                
                # Parse process info if available
                pid = None
                process_name = None
                user = None
                
                if len(parts) > 6:
                    process_info = ' '.join(parts[6:])
                    # Extract from users:(("sshd",pid=1234,fd=3))
                    pid_match = re.search(r'pid=(\d+)', process_info)
                    if pid_match:
                        pid = int(pid_match.group(1))
                    
                    name_match = re.search(r'\("([^"]+)"', process_info)
                    if name_match:
                        process_name = name_match.group(1)
                
                ports.append(PortInfo(
                    port=port,
                    protocol=protocol,
                    address=address,
                    pid=pid,
                    process_name=process_name,
                    user=user
                ))
            except (ValueError, IndexError):
                continue
        
        return ports
    
    def _parse_netstat_output(self, output: str) -> List[PortInfo]:
        """
        Parse 'netstat -tulpn' output.
        
        Format: Proto Recv-Q Send-Q Local Address Foreign Address State PID/Program name
        Example: tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      1234/sshd
        """
        ports = []
        lines = output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Proto') or line.startswith('Active'):
                continue
            
            parts = line.split()
            if len(parts) < 6:
                continue
            
            try:
                protocol = parts[0].lower()
                local_addr = parts[3]
                state = parts[5] if len(parts) > 5 else ""
                
                if state != 'LISTEN' and protocol.startswith('tcp'):
                    continue
                
                # Parse local address:port
                if ':' in local_addr:
                    addr_parts = local_addr.rsplit(':', 1)
                    address = addr_parts[0]
                    port = int(addr_parts[1])
                else:
                    continue
                
                # Parse PID/Program
                pid = None
                process_name = None
                
                if len(parts) > 6:
                    pid_program = parts[6]
                    if '/' in pid_program:
                        pid_str, process_name = pid_program.split('/', 1)
                        try:
                            pid = int(pid_str)
                        except ValueError:
                            pass
                
                ports.append(PortInfo(
                    port=port,
                    protocol=protocol,
                    address=address,
                    pid=pid,
                    process_name=process_name,
                    user=None
                ))
            except (ValueError, IndexError):
                continue
        
        return ports
    
    def _parse_lsof_output(self, output: str) -> List[PortInfo]:
        """
        Parse 'lsof -i -P -n | grep LISTEN' output.
        
        Format: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME
        Example: sshd 1234 root 3u IPv4 12345 0t0 TCP *:22 (LISTEN)
        """
        ports = []
        lines = output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('COMMAND'):
                continue
            
            parts = line.split()
            if len(parts) < 9:
                continue
            
            try:
                process_name = parts[0]
                pid = int(parts[1])
                user = parts[2]
                
                # Parse NAME field (e.g., *:22, 127.0.0.1:3306)
                name_field = parts[8]
                
                # Extract protocol from TYPE field
                protocol = 'tcp'  # Default
                if len(parts) > 7:
                    type_field = parts[7].lower()
                    if 'udp' in type_field:
                        protocol = 'udp'
                
                # Parse address:port
                if ':' in name_field:
                    addr_parts = name_field.rsplit(':', 1)
                    address = addr_parts[0].replace('*', '0.0.0.0')
                    port = int(addr_parts[1].split('(')[0])  # Remove (LISTEN) if present
                else:
                    continue
                
                ports.append(PortInfo(
                    port=port,
                    protocol=protocol,
                    address=address,
                    pid=pid,
                    process_name=process_name,
                    user=user
                ))
            except (ValueError, IndexError):
                continue
        
        return ports
    
    def _match_ports(
        self,
        ports: List[PortInfo],
        ssh_exec: Callable[[str], Tuple[str, str, int]]
    ) -> List[ApplicationInstance]:
        """
        Match ports against application signatures.
        
        Args:
            ports: List of listening ports
            ssh_exec: Function to execute SSH commands
            
        Returns:
            List of detected application instances
        """
        detected: Dict[str, ApplicationInstance] = {}
        
        for port_info in ports:
            # Try to match against all signatures
            matches = self.signature_db.match_port(port_info.port)
            
            for signature in matches:
                app_key = f"{signature.name}_{port_info.port}"
                
                if app_key not in detected:
                    # Create new application instance
                    version = self._detect_version(signature, port_info, ssh_exec)
                    
                    network_binding = NetworkBinding(
                        port=port_info.port,
                        protocol=port_info.protocol,
                        address=port_info.address,
                        process_name=port_info.process_name
                    )
                    
                    app_instance = ApplicationInstance(
                        name=signature.name,
                        category=signature.category,
                        version=version or "unknown",
                        vendor=signature.vendor,
                        detection_methods=[DetectionMethod.PORT_SCAN],
                        confidence=self._calculate_confidence(signature, port_info, version),
                        process_info={
                            'pid': port_info.pid,
                            'process_name': port_info.process_name,
                            'user': port_info.user
                        } if port_info.pid else {},
                        network_bindings=[network_binding],
                        config_files=[],
                        install_path=None
                    )
                    
                    detected[app_key] = app_instance
                else:
                    # Add additional network binding
                    existing = detected[app_key]
                    network_binding = NetworkBinding(
                        port=port_info.port,
                        protocol=port_info.protocol,
                        address=port_info.address,
                        process_name=port_info.process_name
                    )
                    existing.network_bindings.append(network_binding)
        
        return list(detected.values())
    
    def _detect_version(
        self,
        signature: ApplicationSignature,
        port_info: PortInfo,
        ssh_exec: Callable[[str], Tuple[str, str, int]]
    ) -> Optional[str]:
        """
        Detect application version.
        
        Args:
            signature: Application signature
            port_info: Port information
            ssh_exec: Function to execute SSH commands
            
        Returns:
            Detected version string or None
        """
        # Try version commands from signature
        for cmd in signature.version_commands:
            try:
                stdout, stderr, exit_code = ssh_exec(cmd)
                
                if exit_code == 0:
                    version = self.signature_db.extract_version(signature, stdout)
                    if version:
                        return version
                    
                    version = self.signature_db.extract_version(signature, stderr)
                    if version:
                        return version
            except Exception:
                continue
        
        return None
    
    def _calculate_confidence(
        self,
        signature: ApplicationSignature,
        port_info: PortInfo,
        version: Optional[str]
    ) -> ConfidenceLevel:
        """
        Calculate confidence level for detected application.
        
        Args:
            signature: Application signature
            port_info: Port information
            version: Detected version (if any)
            
        Returns:
            Confidence level
        """
        score = 0
        
        # Base score for port match
        score += 30
        
        # Bonus for well-known ports (standard ports are more reliable)
        well_known_ports = {
            22: 'ssh', 80: 'http', 443: 'https', 3306: 'mysql',
            5432: 'postgresql', 1521: 'oracle', 27017: 'mongodb',
            6379: 'redis', 9200: 'elasticsearch'
        }
        if port_info.port in well_known_ports:
            score += 20
        
        # Bonus for process name match
        if port_info.process_name:
            # Check if process name matches signature
            for pattern in signature.compiled_process_patterns:
                if pattern.search(port_info.process_name):
                    score += 30
                    break
        
        # Bonus for version detection
        if version and version != "unknown":
            score += 20
        
        # Convert score to confidence level
        if score >= 80:
            return ConfidenceLevel.HIGH
        elif score >= 60:
            return ConfidenceLevel.MEDIUM
        elif score >= 40:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNCERTAIN
    
    def get_port_statistics(self, ports: List[PortInfo]) -> Dict[str, Any]:
        """
        Get statistics about listening ports.
        
        Args:
            ports: List of port information
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_ports': len(ports),
            'by_protocol': {},
            'by_address': {},
            'port_ranges': {
                'well_known': 0,  # 0-1023
                'registered': 0,  # 1024-49151
                'dynamic': 0  # 49152-65535
            }
        }
        
        for port_info in ports:
            # Count by protocol
            protocol = port_info.protocol
            stats['by_protocol'][protocol] = stats['by_protocol'].get(protocol, 0) + 1
            
            # Count by address
            address = port_info.address
            stats['by_address'][address] = stats['by_address'].get(address, 0) + 1
            
            # Count by port range
            if port_info.port <= 1023:
                stats['port_ranges']['well_known'] += 1
            elif port_info.port <= 49151:
                stats['port_ranges']['registered'] += 1
            else:
                stats['port_ranges']['dynamic'] += 1
        
        return stats

# Made with Bob
