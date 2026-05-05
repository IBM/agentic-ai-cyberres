"""
BeeAI Production Patterns V2 Implementation

This package contains the V2 implementation of the BeeAI agents using
RequirementAgent pattern with Artifact Handoff for agent communication.

Key Components:
- ArtifactStore: Centralized artifact management with versioning
- Agent Factories: Standardized agent creation
- Artifact Schemas: Type-safe agent communication
- Discovery Agent V2: POC implementation
"""

from .artifact_store import ArtifactStore, ArtifactMetadata

__all__ = [
    "ArtifactStore",
    "ArtifactMetadata",
]

__version__ = "2.0.0-alpha"

# Made with Bob
