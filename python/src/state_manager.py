#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Workflow state management for validation workflows."""

import json
import logging
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Workflow execution states."""
    INITIALIZED = "initialized"
    DISCOVERING = "discovering"
    CLASSIFYING = "classifying"
    VALIDATING = "validating"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowContext:
    """Context for workflow execution.
    
    Tracks the complete state of a validation workflow including
    current state, resource information, and results from each phase.
    """
    workflow_id: str
    state: WorkflowState
    resource_info: Dict[str, Any]
    discovery_results: Optional[Dict[str, Any]] = None
    classification: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def can_transition_to(self, new_state: WorkflowState) -> bool:
        """Check if state transition is valid.
        
        Args:
            new_state: Target state
        
        Returns:
            True if transition is valid, False otherwise
        """
        valid_transitions = {
            WorkflowState.INITIALIZED: [WorkflowState.DISCOVERING, WorkflowState.VALIDATING],
            WorkflowState.DISCOVERING: [WorkflowState.CLASSIFYING, WorkflowState.FAILED],
            WorkflowState.CLASSIFYING: [WorkflowState.VALIDATING, WorkflowState.FAILED],
            WorkflowState.VALIDATING: [WorkflowState.REPORTING, WorkflowState.FAILED],
            WorkflowState.REPORTING: [WorkflowState.COMPLETED, WorkflowState.FAILED],
            WorkflowState.FAILED: [],  # Terminal state
            WorkflowState.COMPLETED: []  # Terminal state
        }
        return new_state in valid_transitions.get(self.state, [])
    
    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now().isoformat()
    
    def add_error(self, error: str):
        """Add an error to the context.
        
        Args:
            error: Error message
        """
        self.errors.append(error)
        self.update_timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary.
        
        Returns:
            Dictionary representation
        """
        data = asdict(self)
        data['state'] = self.state.value
        return data


class StateManager:
    """Manages workflow state persistence.
    
    Provides functionality to save and load workflow state to/from disk,
    enabling checkpoint/resume capabilities and audit trails.
    """
    
    def __init__(self, state_dir: str = ".workflow_states"):
        """Initialize state manager.
        
        Args:
            state_dir: Directory to store workflow states
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
        logger.info(f"State manager initialized with directory: {self.state_dir}")
    
    async def save_state(self, context: WorkflowContext):
        """Save workflow state to disk.
        
        Args:
            context: Workflow context to save
        """
        try:
            context.update_timestamp()
            state_file = self.state_dir / f"{context.workflow_id}.json"
            
            with open(state_file, 'w') as f:
                json.dump(context.to_dict(), f, indent=2)
            
            logger.debug(
                f"Saved workflow state",
                extra={
                    "workflow_id": context.workflow_id,
                    "state": context.state.value,
                    "file": str(state_file)
                }
            )
        except Exception as e:
            logger.error(f"Failed to save workflow state: {e}", exc_info=True)
            raise
    
    async def load_state(self, workflow_id: str) -> Optional[WorkflowContext]:
        """Load workflow state from disk.
        
        Args:
            workflow_id: Workflow identifier
        
        Returns:
            WorkflowContext if found, None otherwise
        """
        try:
            state_file = self.state_dir / f"{workflow_id}.json"
            
            if not state_file.exists():
                logger.warning(f"Workflow state not found: {workflow_id}")
                return None
            
            with open(state_file, 'r') as f:
                data = json.load(f)
            
            # Convert state string back to enum
            data['state'] = WorkflowState(data['state'])
            
            context = WorkflowContext(**data)
            
            logger.debug(
                f"Loaded workflow state",
                extra={
                    "workflow_id": workflow_id,
                    "state": context.state.value
                }
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to load workflow state: {e}", exc_info=True)
            return None
    
    async def delete_state(self, workflow_id: str) -> bool:
        """Delete workflow state from disk.
        
        Args:
            workflow_id: Workflow identifier
        
        Returns:
            True if deleted, False if not found
        """
        try:
            state_file = self.state_dir / f"{workflow_id}.json"
            
            if state_file.exists():
                state_file.unlink()
                logger.info(f"Deleted workflow state: {workflow_id}")
                return True
            else:
                logger.warning(f"Workflow state not found for deletion: {workflow_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete workflow state: {e}", exc_info=True)
            return False
    
    def list_workflows(self, state_filter: Optional[WorkflowState] = None) -> List[str]:
        """List all workflow IDs, optionally filtered by state.
        
        Args:
            state_filter: Optional state to filter by
        
        Returns:
            List of workflow IDs
        """
        try:
            workflow_ids = []
            
            for state_file in self.state_dir.glob("*.json"):
                workflow_id = state_file.stem
                
                if state_filter:
                    # Load and check state
                    with open(state_file, 'r') as f:
                        data = json.load(f)
                    
                    if WorkflowState(data['state']) == state_filter:
                        workflow_ids.append(workflow_id)
                else:
                    workflow_ids.append(workflow_id)
            
            return workflow_ids
            
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}", exc_info=True)
            return []


# Made with Bob