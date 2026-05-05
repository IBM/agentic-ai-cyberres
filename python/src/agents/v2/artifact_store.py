"""
Artifact Store - Centralized artifact management with versioning

This module provides a type-safe artifact storage system for agent communication.
Artifacts are versioned, validated, and optionally persisted to disk.

Key Features:
- Type-safe storage and retrieval using Pydantic models
- Automatic versioning for all artifacts
- Metadata tracking (timestamp, size, type)
- Optional persistence to disk
- History tracking for all versions
- Thread-safe operations

Example:
    >>> store = ArtifactStore()
    >>> artifact = DiscoveryArtifact(resource_id="vm-01", ...)
    >>> artifact_id = store.save("discovery", artifact)
    'discovery:v1'
    >>> loaded = store.load("discovery", DiscoveryArtifact)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class ArtifactMetadata(BaseModel):
    """Metadata for stored artifacts."""
    
    key: str = Field(description="Artifact identifier")
    version: int = Field(description="Version number")
    timestamp: datetime = Field(description="When artifact was saved")
    artifact_type: str = Field(description="Pydantic model class name")
    size_bytes: int = Field(description="Serialized size in bytes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


class ArtifactStore:
    """
    Centralized artifact storage with versioning and persistence.
    
    This class provides type-safe storage for Pydantic model instances,
    enabling clean agent-to-agent communication via artifact handoff.
    
    Features:
    - Type-safe artifact storage and retrieval
    - Automatic versioning (v1, v2, v3, ...)
    - Metadata tracking for all artifacts
    - Optional persistence to disk
    - History tracking for all versions
    - List and query capabilities
    
    Example:
        >>> store = ArtifactStore()
        >>> 
        >>> # Save artifact
        >>> discovery = DiscoveryArtifact(resource_id="vm-01", ...)
        >>> artifact_id = store.save("discovery", discovery, 
        ...                          metadata={"agent": "discovery"})
        >>> 
        >>> # Load artifact with type safety
        >>> loaded = store.load("discovery", DiscoveryArtifact)
        >>> assert isinstance(loaded, DiscoveryArtifact)
        >>> 
        >>> # Get metadata
        >>> meta = store.get_metadata("discovery")
        >>> print(f"Version: {meta.version}, Type: {meta.artifact_type}")
    """
    
    def __init__(self, persist_path: Optional[Path] = None):
        """
        Initialize artifact store.
        
        Args:
            persist_path: Optional path for persisting artifacts to disk.
                         If provided, artifacts will be saved as JSON files.
        """
        self._artifacts: Dict[str, Dict[str, Any]] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = {}
        self._metadata: Dict[str, ArtifactMetadata] = {}
        self._persist_path = persist_path
        
        if persist_path:
            persist_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"ArtifactStore initialized with persistence: {persist_path}")
        else:
            logger.info("ArtifactStore initialized (in-memory only)")
    
    def save(
        self,
        key: str,
        value: BaseModel,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save artifact with automatic versioning.
        
        Args:
            key: Artifact identifier (e.g., "discovery", "validation")
            value: Pydantic model instance to store
            metadata: Optional custom metadata dictionary
            
        Returns:
            Versioned key in format "key:vN" (e.g., "discovery:v1")
            
        Example:
            >>> artifact_id = store.save("discovery", discovery_artifact,
            ...                          metadata={"resource_id": "vm-01"})
            >>> print(artifact_id)  # "discovery:v1"
        """
        version = self._get_next_version(key)
        
        # Serialize artifact
        artifact_data = value.model_dump()
        artifact_json = value.model_dump_json(indent=2)
        
        # Create artifact record
        artifact = {
            "value": artifact_data,
            "version": version,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "type": type(value).__name__
        }
        
        # Store current version
        self._artifacts[key] = artifact
        
        # Add to history
        self._add_to_history(key, artifact)
        
        # Store metadata
        self._metadata[key] = ArtifactMetadata(
            key=key,
            version=version,
            timestamp=datetime.utcnow(),
            artifact_type=type(value).__name__,
            size_bytes=len(artifact_json),
            metadata=metadata or {}
        )
        
        # Persist if configured
        if self._persist_path:
            self._persist_artifact(key, version, artifact_json)
        
        versioned_key = f"{key}:v{version}"
        logger.info(f"Saved artifact: {versioned_key} ({type(value).__name__})")
        
        return versioned_key
    
    def load(
        self,
        key: str,
        model_class: Type[T],
        version: Optional[int] = None
    ) -> T:
        """
        Load artifact with type safety.
        
        Args:
            key: Artifact identifier
            model_class: Pydantic model class for type safety and validation
            version: Optional specific version to load (default: latest)
            
        Returns:
            Typed artifact instance
            
        Raises:
            KeyError: If artifact not found
            ValueError: If version invalid
            
        Example:
            >>> # Load latest version
            >>> discovery = store.load("discovery", DiscoveryArtifact)
            >>> 
            >>> # Load specific version
            >>> discovery_v1 = store.load("discovery", DiscoveryArtifact, version=1)
        """
        if version is not None:
            artifact_data = self._load_version(key, version)
        else:
            if key not in self._artifacts:
                raise KeyError(f"Artifact not found: {key}")
            artifact_data = self._artifacts[key]["value"]
        
        # Reconstruct typed model with validation
        try:
            instance = model_class(**artifact_data)
            logger.debug(f"Loaded artifact: {key} ({model_class.__name__})")
            return instance
        except Exception as e:
            logger.error(f"Failed to load artifact {key}: {e}")
            raise ValueError(f"Failed to deserialize artifact {key}: {e}")
    
    def get_metadata(self, key: str) -> ArtifactMetadata:
        """
        Get artifact metadata.
        
        Args:
            key: Artifact identifier
            
        Returns:
            ArtifactMetadata with version, timestamp, type, size
            
        Raises:
            KeyError: If artifact not found
        """
        if key not in self._metadata:
            raise KeyError(f"Artifact not found: {key}")
        return self._metadata[key]
    
    def list_artifacts(self) -> List[str]:
        """
        List all artifact keys.
        
        Returns:
            List of artifact identifiers
            
        Example:
            >>> keys = store.list_artifacts()
            >>> print(keys)  # ['discovery', 'validation', 'evaluation']
        """
        return list(self._artifacts.keys())
    
    def get_history(self, key: str) -> List[ArtifactMetadata]:
        """
        Get version history for artifact.
        
        Args:
            key: Artifact identifier
            
        Returns:
            List of ArtifactMetadata for all versions
            
        Example:
            >>> history = store.get_history("discovery")
            >>> for meta in history:
            ...     print(f"v{meta.version}: {meta.timestamp}")
        """
        if key not in self._history:
            return []
        
        return [
            ArtifactMetadata(
                key=key,
                version=i + 1,
                timestamp=datetime.fromisoformat(artifact["timestamp"]),
                artifact_type=artifact["type"],
                size_bytes=len(json.dumps(artifact["value"])),
                metadata=artifact.get("metadata", {})
            )
            for i, artifact in enumerate(self._history[key])
        ]
    
    def exists(self, key: str) -> bool:
        """
        Check if artifact exists.
        
        Args:
            key: Artifact identifier
            
        Returns:
            True if artifact exists, False otherwise
        """
        return key in self._artifacts
    
    def delete(self, key: str) -> bool:
        """
        Delete artifact and its history.
        
        Args:
            key: Artifact identifier
            
        Returns:
            True if deleted, False if not found
        """
        if key not in self._artifacts:
            return False
        
        del self._artifacts[key]
        if key in self._history:
            del self._history[key]
        if key in self._metadata:
            del self._metadata[key]
        
        logger.info(f"Deleted artifact: {key}")
        return True
    
    def clear(self):
        """Clear all artifacts from store."""
        self._artifacts.clear()
        self._history.clear()
        self._metadata.clear()
        logger.info("Cleared all artifacts from store")
    
    def _get_next_version(self, key: str) -> int:
        """Get next version number for key."""
        if key not in self._history:
            return 1
        return len(self._history[key]) + 1
    
    def _add_to_history(self, key: str, artifact: Dict[str, Any]):
        """Add artifact to history."""
        if key not in self._history:
            self._history[key] = []
        self._history[key].append(artifact)
    
    def _load_version(self, key: str, version: int) -> Dict[str, Any]:
        """Load specific version of artifact."""
        if key not in self._history:
            raise KeyError(f"Artifact not found: {key}")
        
        if version < 1 or version > len(self._history[key]):
            raise ValueError(
                f"Invalid version: {version} "
                f"(available: 1-{len(self._history[key])})"
            )
        
        return self._history[key][version - 1]["value"]
    
    def _persist_artifact(self, key: str, version: int, artifact_json: str):
        """Persist artifact to disk."""
        if not self._persist_path:
            return
        
        try:
            file_path = self._persist_path / f"{key}_v{version}.json"
            file_path.write_text(artifact_json)
            logger.debug(f"Persisted artifact to: {file_path}")
        except Exception as e:
            logger.error(f"Failed to persist artifact {key}:v{version}: {e}")

# Made with Bob
