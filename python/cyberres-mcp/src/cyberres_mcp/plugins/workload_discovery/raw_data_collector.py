"""
Copyright contributors to the agentic-ai-cyberres project
"""

"""Raw data collection for agent-side processing."""

from typing import Dict, Any, List, Optional, Callable, Tuple
import logging
import shlex

logger = logging.getLogger("mcp.workload_discovery.raw_data_collector")


class RawDataCollector:
    """Collects raw server data for agent-side LLM processing."""
    
    def collect(
        self, 
        ssh_exec: Callable[[str], Tuple[int, str, str]], 
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Collect raw data from server.
        
        Args:
            ssh_exec: SSH execution function that returns (exit_code, stdout, stderr)
            options: Collection options specifying what to collect
            
        Returns:
            Dictionary with raw data:
            {
                "processes": "...",  # Raw ps output
                "ports": "...",      # Raw netstat/ss output
                "configs": {...},    # Config file contents
                "packages": "...",   # Package list
                "services": "..."    # Service list
            }
        """
        options = options or {}
        result = {}
        
        try:
            # Collect process list
            if options.get("collect_processes", True):
                logger.info("Collecting process list...")
                result["processes"] = self._collect_processes(ssh_exec)
            
            # Collect port list
            if options.get("collect_ports", True):
                logger.info("Collecting port list...")
                result["ports"] = self._collect_ports(ssh_exec)
            
            # Collect config files
            if options.get("collect_configs", False):
                config_paths = options.get("config_paths", [])
                if config_paths:
                    logger.info(f"Collecting {len(config_paths)} config files...")
                    result["configs"] = self._collect_configs(ssh_exec, config_paths)
            
            # Collect package list
            if options.get("collect_packages", False):
                logger.info("Collecting package list...")
                result["packages"] = self._collect_packages(ssh_exec)
            
            # Collect service list
            if options.get("collect_services", False):
                logger.info("Collecting service list...")
                result["services"] = self._collect_services(ssh_exec)
            
            logger.info(f"Raw data collection complete. Collected {len(result)} data types.")
            return result
            
        except Exception as e:
            logger.error(f"Raw data collection failed: {str(e)}")
            return {"error": str(e)}
    
    def _collect_processes(self, ssh_exec: Callable) -> str:
        """
        Collect process list.
        
        Returns:
            Raw ps output or empty string on failure
        """
        try:
            exit_code, stdout, stderr = ssh_exec("ps aux")
            if exit_code == 0 and stdout:
                logger.debug(f"Collected {len(stdout.splitlines())} processes")
                return stdout
            else:
                logger.warning(f"Process collection failed: exit_code={exit_code}, stderr={stderr}")
                return ""
        except Exception as e:
            logger.error(f"Process collection error: {str(e)}")
            return ""
    
    def _collect_ports(self, ssh_exec: Callable) -> str:
        """
        Collect listening ports.
        
        Tries netstat first, falls back to ss.
        
        Returns:
            Raw netstat/ss output or empty string on failure
        """
        try:
            # Try netstat first
            exit_code, stdout, stderr = ssh_exec("netstat -tulpn 2>/dev/null")
            if exit_code == 0 and stdout:
                logger.debug(f"Collected ports using netstat: {len(stdout.splitlines())} lines")
                return stdout
            
            # Fallback to ss
            exit_code, stdout, stderr = ssh_exec("ss -tulpn 2>/dev/null")
            if exit_code == 0 and stdout:
                logger.debug(f"Collected ports using ss: {len(stdout.splitlines())} lines")
                return stdout
            
            logger.warning("Port collection failed with both netstat and ss")
            return ""
            
        except Exception as e:
            logger.error(f"Port collection error: {str(e)}")
            return ""
    
    def _collect_configs(
        self, 
        ssh_exec: Callable, 
        paths: List[str]
    ) -> Dict[str, str]:
        """
        Collect configuration files.
        
        Args:
            ssh_exec: SSH execution function
            paths: List of config file paths to collect
            
        Returns:
            Dictionary mapping path to file contents
        """
        configs = {}
        
        for path in paths:
            try:
                quoted_path = shlex.quote(path)
                exit_code, stdout, stderr = ssh_exec(f"cat -- {quoted_path} 2>/dev/null")
                if exit_code == 0 and stdout:
                    configs[path] = stdout
                    logger.debug(f"Collected config: {path} ({len(stdout)} bytes)")
                else:
                    logger.warning(f"Failed to collect config {path}: exit_code={exit_code}")
            except Exception as e:
                logger.error(f"Config collection error for {path}: {str(e)}")
        
        return configs
    
    def _collect_packages(self, ssh_exec: Callable) -> str:
        """
        Collect installed packages.
        
        Tries rpm first (RHEL/CentOS), then dpkg (Debian/Ubuntu).
        
        Returns:
            Raw package list or empty string on failure
        """
        try:
            # Try rpm (RHEL/CentOS/Oracle Linux)
            exit_code, stdout, stderr = ssh_exec("rpm -qa 2>/dev/null")
            if exit_code == 0 and stdout:
                logger.debug(f"Collected packages using rpm: {len(stdout.splitlines())} packages")
                return stdout
            
            # Try dpkg (Debian/Ubuntu)
            exit_code, stdout, stderr = ssh_exec("dpkg -l 2>/dev/null")
            if exit_code == 0 and stdout:
                logger.debug(f"Collected packages using dpkg: {len(stdout.splitlines())} packages")
                return stdout
            
            logger.warning("Package collection failed with both rpm and dpkg")
            return ""
            
        except Exception as e:
            logger.error(f"Package collection error: {str(e)}")
            return ""
    
    def _collect_services(self, ssh_exec: Callable) -> str:
        """
        Collect running services.
        
        Tries systemctl first, falls back to service command.
        
        Returns:
            Raw service list or empty string on failure
        """
        try:
            # Try systemctl (modern systems)
            exit_code, stdout, stderr = ssh_exec("systemctl list-units --type=service 2>/dev/null")
            if exit_code == 0 and stdout:
                logger.debug(f"Collected services using systemctl: {len(stdout.splitlines())} services")
                return stdout
            
            # Try service command (older systems)
            exit_code, stdout, stderr = ssh_exec("service --status-all 2>/dev/null")
            if exit_code == 0 and stdout:
                logger.debug(f"Collected services using service: {len(stdout.splitlines())} services")
                return stdout
            
            logger.warning("Service collection failed with both systemctl and service")
            return ""
            
        except Exception as e:
            logger.error(f"Service collection error: {str(e)}")
            return ""

# Made with Bob
