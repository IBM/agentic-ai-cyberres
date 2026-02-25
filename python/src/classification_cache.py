#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Classification caching system for cost optimization."""

import hashlib
import logging
import time
from typing import Dict, Optional, Tuple
from models import ResourceClassification, WorkloadDiscoveryResult

logger = logging.getLogger(__name__)


class ClassificationCache:
    """Cache for classification results to reduce LLM costs.
    
    Caches classification results based on discovery data fingerprint.
    Cache key is generated from ports, processes, and detected applications.
    """
    
    def __init__(self, ttl: int = 3600, max_size: int = 1000):
        """Initialize classification cache.
        
        Args:
            ttl: Time-to-live in seconds (default: 1 hour)
            max_size: Maximum cache size (default: 1000 entries)
        """
        self._cache: Dict[str, Tuple[ResourceClassification, float]] = {}
        self._ttl = ttl
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        
        logger.info(f"Classification cache initialized (TTL: {ttl}s, Max size: {max_size})")
    
    def get(self, discovery_result: WorkloadDiscoveryResult) -> Optional[ResourceClassification]:
        """Get cached classification if available and not expired.
        
        Args:
            discovery_result: Discovery result to look up
        
        Returns:
            Cached classification or None if not found/expired
        """
        cache_key = self._get_cache_key(discovery_result)
        
        if cache_key in self._cache:
            classification, timestamp = self._cache[cache_key]
            
            # Check if expired
            if time.time() - timestamp < self._ttl:
                self._hits += 1
                logger.debug(
                    f"Cache HIT for {discovery_result.host}",
                    extra={
                        "cache_key": cache_key[:16],
                        "hit_rate": self.get_hit_rate()
                    }
                )
                return classification
            else:
                # Expired - remove from cache
                del self._cache[cache_key]
                logger.debug(f"Cache entry expired for {discovery_result.host}")
        
        self._misses += 1
        logger.debug(
            f"Cache MISS for {discovery_result.host}",
            extra={
                "cache_key": cache_key[:16],
                "hit_rate": self.get_hit_rate()
            }
        )
        return None
    
    def set(self, discovery_result: WorkloadDiscoveryResult, classification: ResourceClassification):
        """Cache classification result.
        
        Args:
            discovery_result: Discovery result
            classification: Classification to cache
        """
        cache_key = self._get_cache_key(discovery_result)
        
        # Check cache size limit
        if len(self._cache) >= self._max_size:
            self._evict_oldest()
        
        self._cache[cache_key] = (classification, time.time())
        
        logger.debug(
            f"Cached classification for {discovery_result.host}",
            extra={
                "cache_key": cache_key[:16],
                "category": classification.category.value,
                "cache_size": len(self._cache)
            }
        )
    
    def _get_cache_key(self, discovery_result: WorkloadDiscoveryResult) -> str:
        """Generate cache key from discovery result.
        
        Cache key is based on:
        - Top 10 ports (sorted)
        - Top 5 process names (sorted)
        - All detected application names (sorted)
        
        Args:
            discovery_result: Discovery result
        
        Returns:
            Cache key (MD5 hash)
        """
        # Extract and sort ports
        ports = sorted([str(p.port) for p in discovery_result.ports[:10]])
        ports_str = ",".join(ports)
        
        # Extract and sort process names
        processes = sorted([p.name for p in discovery_result.processes[:5]])
        procs_str = ",".join(processes)
        
        # Extract and sort application names
        apps = sorted([a.name for a in discovery_result.applications])
        apps_str = ",".join(apps)
        
        # Create fingerprint
        fingerprint = f"{ports_str}|{procs_str}|{apps_str}"
        
        # Generate hash
        cache_key = hashlib.md5(fingerprint.encode()).hexdigest()
        
        logger.debug(
            f"Generated cache key for {discovery_result.host}",
            extra={
                "fingerprint": fingerprint[:100],
                "cache_key": cache_key[:16]
            }
        )
        
        return cache_key
    
    def _evict_oldest(self):
        """Evict oldest cache entry when cache is full."""
        if not self._cache:
            return
        
        # Find oldest entry
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
        
        # Remove it
        del self._cache[oldest_key]
        
        logger.debug(
            "Evicted oldest cache entry",
            extra={"cache_size": len(self._cache)}
        )
    
    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Classification cache cleared")
    
    def get_stats(self) -> Dict[str, any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.get_hit_rate(),
            "total_requests": self._hits + self._misses
        }
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate.
        
        Returns:
            Hit rate as percentage (0-100)
        """
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return (self._hits / total) * 100
    
    def __repr__(self) -> str:
        """String representation of cache.
        
        Returns:
            String representation
        """
        return (
            f"ClassificationCache(size={len(self._cache)}/{self._max_size}, "
            f"hit_rate={self.get_hit_rate():.1f}%, "
            f"hits={self._hits}, misses={self._misses})"
        )


# Global cache instance
_global_cache: Optional[ClassificationCache] = None


def get_cache() -> ClassificationCache:
    """Get global classification cache instance.
    
    Returns:
        Global cache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = ClassificationCache()
    return _global_cache


def clear_cache():
    """Clear global classification cache."""
    global _global_cache
    if _global_cache:
        _global_cache.clear()


# Made with Bob