"""
LLM-based intelligent result aggregation for workload discovery.

This module provides LLM-powered aggregation that:
- Correlates ports with processes intelligently
- Identifies application patterns across data
- Detects dependencies between services
- Infers missing information from context
- Provides confidence scoring with reasoning
"""

import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Import new output management system
from agents.output import AgentResponseParser

logger = logging.getLogger("mcp.workload_discovery.llm_aggregator")


class LLMAggregator:
    """
    LLM-based aggregator for intelligent workload discovery correlation.
    
    Uses LLM to:
    1. Correlate ports with processes (e.g., port 3306 + mysqld = MySQL)
    2. Identify application patterns and dependencies
    3. Infer missing information from partial data
    4. Provide reasoning for detection decisions
    5. Score confidence based on evidence quality
    """
    
    def __init__(self, llm_model: str = "ollama:llama3.2"):
        """
        Initialize LLM aggregator.
        
        Args:
            llm_model: LLM model identifier (e.g., "ollama:llama3.2", "openai:gpt-4")
        """
        self.llm_model = llm_model
        self._llm = None
        self._parser = AgentResponseParser()  # Initialize response parser
        logger.info(f"LLM Aggregator initialized with model: {llm_model}")
    
    def _get_agent(self):
        """Lazy load BeeAI agent to avoid import issues."""
        if self._llm is None:
            try:
                from beeai_framework.agents.react.agent import ReActAgent
                from beeai_framework.backend.chat import ChatModel
                from beeai_framework.memory import SlidingMemory, SlidingMemoryConfig
                
                llm = ChatModel.from_name(self.llm_model)
                memory = SlidingMemory(SlidingMemoryConfig(size=10))
                
                self._llm = ReActAgent(
                    llm=llm,
                    memory=memory,
                    tools=[]  # No tools needed for aggregation
                )
                logger.info("LLM agent loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load LLM agent: {e}, falling back to deterministic")
                self._llm = None
        return self._llm
    
    async def aggregate(
        self,
        ports: List[Dict[str, Any]],
        processes: List[Dict[str, Any]],
        applications: List[Dict[str, Any]],
        os_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Aggregate discovery results using LLM intelligence.
        
        Args:
            ports: List of discovered ports
            processes: List of running processes
            applications: List of detected applications
            os_info: Optional OS information
        
        Returns:
            Enhanced discovery result with intelligent correlations
        """
        logger.info(
            f"Starting LLM aggregation: {len(ports)} ports, "
            f"{len(processes)} processes, {len(applications)} apps"
        )
        
        # Try LLM aggregation first
        try:
            agent = self._get_agent()
            if agent:
                result = await self._llm_aggregate(
                    ports, processes, applications, os_info
                )
                logger.info("LLM aggregation successful")
                return result
        except Exception as e:
            logger.warning(f"LLM aggregation failed: {e}, using deterministic fallback")
        
        # Fallback to deterministic aggregation
        return self._deterministic_aggregate(ports, processes, applications, os_info)
    
    async def _llm_aggregate(
        self,
        ports: List[Dict[str, Any]],
        processes: List[Dict[str, Any]],
        applications: List[Dict[str, Any]],
        os_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Use LLM to intelligently aggregate and correlate discovery data.
        
        Args:
            ports: Discovered ports
            processes: Running processes
            applications: Detected applications
            os_info: OS information
        
        Returns:
            Enhanced aggregation result
        """
        agent = self._get_agent()
        
        # Build analysis prompt
        prompt = self._build_aggregation_prompt(ports, processes, applications, os_info)
        
        # Get LLM analysis using BeeAI agent (same pattern as other agents)
        response = await agent.run(prompt)
        logger.info(f"✓ Got LLM response, type: {type(response)}, is list: {isinstance(response, list)}")
        if isinstance(response, list) and len(response) > 0:
            logger.info(f"  First item type: {type(response[0])}")
            logger.info(f"  Last item type: {type(response[-1])}")
        
        # Extract the actual text content from BeeAI response
        logger.info("Calling _extract_response_text()...")
        response_text = self._extract_response_text(response)
        logger.info(f"✓ _extract_response_text() returned: type={type(response_text)}, length={len(response_text)}")
        
        logger.info(f"Response extracted, length: {len(response_text)}, type: {type(response_text)}")
        if response_text:
            logger.info(f"Response preview (first 300 chars): {response_text[:300]}")
            logger.debug(f"Full response text: {response_text}")
        
        # Parse LLM response
        analysis = self._parse_llm_response(response_text)
        
        # Ensure analysis is a valid dictionary
        if analysis is None or not isinstance(analysis, dict):
            logger.warning(f"Invalid analysis result: {type(analysis)}, using fallback")
            analysis = {
                "correlations": [],
                "dependencies": [],
                "insights": ["LLM analysis returned invalid result"],
                "missing_data": [],
                "recommendations": []
            }
        
        # Enhance applications with LLM insights
        enhanced_apps = self._enhance_applications(applications, analysis)
        
        # Add correlations
        correlations = analysis.get("correlations", [])
        
        # Add dependencies
        dependencies = analysis.get("dependencies", [])
        
        return {
            "ports": ports,
            "processes": processes,
            "applications": enhanced_apps,
            "os_info": os_info,
            "correlations": correlations,
            "dependencies": dependencies,
            "llm_insights": analysis.get("insights", []),
            "aggregation_method": "llm",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _extract_response_text(self, response: Any) -> str:
        """
        Extract text content from BeeAI agent response.
        
        Uses the new AgentResponseParser for consistent response extraction.
        
        Args:
            response: Response from BeeAI agent (typically a list of messages)
        
        Returns:
            Extracted text content as string
        """
        return self._parser.extract_simple_text(response)
    
    def _build_aggregation_prompt(
        self,
        ports: List[Dict[str, Any]],
        processes: List[Dict[str, Any]],
        applications: List[Dict[str, Any]],
        os_info: Optional[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for LLM aggregation analysis.
        
        Args:
            ports: Discovered ports
            processes: Running processes
            applications: Detected applications
            os_info: OS information
        
        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "# Workload Discovery Aggregation Task",
            "",
            "You are an expert system administrator analyzing workload discovery data.",
            "Your task is to intelligently correlate ports, processes, and applications",
            "to provide comprehensive insights about the system.",
            "",
            "IMPORTANT: You MUST respond with ONLY valid JSON. Do not include any explanatory text before or after the JSON.",
            "",
            "## Discovered Data",
            ""
        ]
        
        # Add ports
        if ports:
            prompt_parts.append("### Open Ports")
            for port in ports[:10]:  # Limit to first 10
                port_num = port.get('port', 'unknown')
                service = port.get('service', 'unknown')
                prompt_parts.append(f"- Port {port_num}: {service}")
            if len(ports) > 10:
                prompt_parts.append(f"- ... and {len(ports) - 10} more ports")
            prompt_parts.append("")
        
        # Add processes
        if processes:
            prompt_parts.append("### Running Processes")
            for proc in processes[:10]:  # Limit to first 10
                name = proc.get('name', 'unknown')
                cmdline = proc.get('cmdline', '')
                prompt_parts.append(f"- {name}: {cmdline[:80]}")
            if len(processes) > 10:
                prompt_parts.append(f"- ... and {len(processes) - 10} more processes")
            prompt_parts.append("")
        
        # Add applications
        if applications:
            prompt_parts.append("### Detected Applications")
            for app in applications:
                name = app.get('name', 'unknown')
                confidence = app.get('confidence', 0)
                method = app.get('detection_method', 'unknown')
                prompt_parts.append(
                    f"- {name} (confidence: {confidence:.0%}, method: {method})"
                )
            prompt_parts.append("")
        
        # Add OS info
        if os_info:
            prompt_parts.append("### Operating System")
            os_name = os_info.get('os_name', 'unknown')
            os_version = os_info.get('os_version', 'unknown')
            prompt_parts.append(f"- OS: {os_name} {os_version}")
            prompt_parts.append("")
        
        # Add analysis instructions
        prompt_parts.extend([
            "## Your Analysis Task",
            "",
            "Respond with ONLY the following JSON structure (no markdown, no explanations):",
            "",
            "{",
            '  "correlations": [',
            '    {',
            '      "port": 3306,',
            '      "process": "mysqld",',
            '      "application": "MySQL",',
            '      "confidence": 0.95,',
            '      "reasoning": "Port 3306 is MySQL default, mysqld process confirms"',
            '    }',
            '  ],',
            '  "dependencies": [',
            '    {',
            '      "service": "nginx",',
            '      "depends_on": ["php-fpm"],',
            '      "reasoning": "Nginx reverse proxy to PHP-FPM"',
            '    }',
            '  ],',
            '  "insights": [',
            '    "This appears to be a LAMP stack server",',
            '    "MySQL is running on default port with standard configuration"',
            '  ],',
            '  "missing_data": [',
            '    "No web server process detected despite port 80 being open"',
            '  ],',
            '  "recommendations": [',
            '    "Verify MySQL is properly secured",',
            '    "Check if web server is configured correctly"',
            '  ]',
            "}",
            "",
            "CRITICAL: Return ONLY the JSON object above. No markdown code blocks, no explanations.",
            "",
            "Focus on:",
            "1. **Correlations**: Link ports to processes and applications",
            "2. **Dependencies**: Identify service dependencies",
            "3. **Insights**: High-level observations about the system",
            "4. **Missing Data**: What's expected but not found",
            "5. **Recommendations**: Actionable suggestions",
            "",
            "Be specific and provide reasoning for your conclusions."
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured data.
        
        Args:
            response: LLM response text
        
        Returns:
            Parsed analysis dictionary
        """
        try:
            # Ensure response is a string
            if not isinstance(response, str):
                logger.warning(f"Response is not a string, got {type(response)}, converting...")
                response = str(response)
            
            logger.debug(f"Parsing response (length={len(response)}): {response[:500]}")
            
            # Try to extract JSON from response with improved logic
            json_str = response.strip()
            
            # Remove common markdown code block markers
            if "```json" in json_str:
                start = json_str.find("```json") + 7
                end = json_str.find("```", start)
                if end > start:
                    json_str = json_str[start:end].strip()
                    logger.debug(f"Extracted from ```json block: {json_str[:200]}")
            elif "```" in json_str:
                start = json_str.find("```") + 3
                end = json_str.find("```", start)
                if end > start:
                    json_str = json_str[start:end].strip()
                    logger.debug(f"Extracted from ``` block: {json_str[:200]}")
            
            # Remove any leading/trailing text before/after JSON object
            if not json_str.startswith('{'):
                # Look for first { and last }
                start_idx = json_str.find('{')
                end_idx = json_str.rfind('}')
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = json_str[start_idx:end_idx+1]
                    logger.debug(f"Extracted JSON from boundaries: {json_str[:200]}")
                else:
                    logger.warning("No JSON object found in response")
                    logger.warning(f"Response content: {response[:1000]}")
                    raise ValueError("No JSON object found in LLM response")
            
            # Parse JSON
            logger.debug(f"Attempting to parse JSON: {json_str[:300]}")
            analysis = json.loads(json_str)
            logger.info(f"✓ Successfully parsed LLM response with {len(analysis)} keys")
            return analysis
        
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️  JSON decode error: {e}")
            if 'json_str' in locals():
                logger.warning(f"⚠️  Failed JSON string (first 500 chars): {json_str[:500]}")
            else:
                logger.warning(f"⚠️  Failed to extract JSON from response (first 500 chars): {response[:500]}")
            logger.info("Instruction: Provide a JSON response with the specified structure, focusing on correlations between ports, processes, and applications.")
            # Return minimal structure
            return {
                "correlations": [],
                "dependencies": [],
                "insights": ["LLM response parsing failed - invalid JSON"],
                "missing_data": [],
                "recommendations": []
            }
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            logger.warning(f"Response preview: {response[:500]}")
            # Return minimal structure
            return {
                "correlations": [],
                "dependencies": [],
                "insights": [f"LLM response parsing failed: {str(e)}"],
                "missing_data": [],
                "recommendations": []
            }
    
    def _enhance_applications(
        self,
        applications: List[Dict[str, Any]],
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Enhance application detections with LLM insights.
        
        Args:
            applications: Original application detections
            analysis: LLM analysis results
        
        Returns:
            Enhanced application list
        """
        enhanced = []
        correlations = analysis.get("correlations", [])
        
        for app in applications:
            enhanced_app = app.copy()
            
            # Find correlations for this app
            app_correlations = [
                c for c in correlations
                if c.get("application", "").lower() == app.get("name", "").lower()
            ]
            
            if app_correlations:
                # Add correlation evidence
                if "evidence" not in enhanced_app:
                    enhanced_app["evidence"] = {}
                
                enhanced_app["evidence"]["llm_correlations"] = app_correlations
                
                # Update confidence if LLM provides higher confidence
                llm_confidence = max(
                    (c.get("confidence", 0) for c in app_correlations),
                    default=0
                )
                if llm_confidence > enhanced_app.get("confidence", 0):
                    enhanced_app["confidence"] = llm_confidence
                    enhanced_app["detection_method"] = "llm_enhanced"
            
            enhanced.append(enhanced_app)
        
        return enhanced
    
    def _deterministic_aggregate(
        self,
        ports: List[Dict[str, Any]],
        processes: List[Dict[str, Any]],
        applications: List[Dict[str, Any]],
        os_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fallback deterministic aggregation when LLM is unavailable.
        
        Args:
            ports: Discovered ports
            processes: Running processes
            applications: Detected applications
            os_info: OS information
        
        Returns:
            Basic aggregation result
        """
        logger.info("Using deterministic aggregation (fallback)")
        
        # Simple port-to-process correlation
        correlations = []
        for port in ports:
            port_num = port.get('port')
            service = port.get('service', '').lower()
            
            # Find matching processes
            for proc in processes:
                proc_name = proc.get('name', '').lower()
                if service and service in proc_name:
                    correlations.append({
                        "port": port_num,
                        "process": proc.get('name'),
                        "confidence": 0.7,
                        "reasoning": f"Service name '{service}' matches process '{proc_name}'"
                    })
        
        return {
            "ports": ports,
            "processes": processes,
            "applications": applications,
            "os_info": os_info,
            "correlations": correlations,
            "dependencies": [],
            "llm_insights": ["Deterministic aggregation used (LLM unavailable)"],
            "aggregation_method": "deterministic",
            "timestamp": datetime.utcnow().isoformat()
        }


# Made with Bob