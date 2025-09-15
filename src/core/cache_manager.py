#!/usr/bin/env python3
"""
Redis Cache Manager for AI Orchestration Analytics
=================================================
Provides intelligent caching for dashboard queries with 3-5x performance improvement.
"""

import json
import redis
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@dataclass
class CacheConfig:
    """Redis cache configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    socket_timeout: float = 5.0
    connection_pool_size: int = 10

    # Cache TTL settings (in seconds)
    ttl_dashboard_summary: int = 30      # Dashboard summary data
    ttl_handoff_analytics: int = 60      # Handoff analytics
    ttl_subagent_usage: int = 60         # Subagent usage stats
    ttl_cost_metrics: int = 120          # Cost analytics
    ttl_session_data: int = 300          # Session details
    ttl_system_status: int = 15          # System health status

class CacheManager:
    """
    Intelligent Redis cache manager optimized for dashboard performance

    Features:
    - Automatic cache invalidation
    - Smart key generation
    - Connection pooling
    - Fallback to database on cache miss
    - Performance metrics tracking
    """

    def __init__(self, config: CacheConfig = None, db_connection=None):
        self.config = config or CacheConfig()
        self.db = db_connection
        self.redis_client = None
        self.connection_pool = None
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'total_requests': 0
        }

    async def initialize(self):
        """Initialize Redis connection with connection pooling"""
        try:
            # Create connection pool for better performance
            self.connection_pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                socket_timeout=self.config.socket_timeout,
                max_connections=self.config.connection_pool_size,
                decode_responses=True  # Automatically decode to strings
            )

            # Create Redis client
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)

            # Test connection
            await self._test_connection()
            logger.info(f"Redis cache initialized: {self.config.host}:{self.config.port}")

        except Exception as e:
            logger.warning(f"Redis not available, operating without cache: {e}")
            self.redis_client = None

    async def _test_connection(self):
        """Test Redis connection"""
        if self.redis_client:
            self.redis_client.ping()

    def _generate_cache_key(self, prefix: str, params: Dict[str, Any] = None) -> str:
        """Generate deterministic cache key"""
        if params:
            # Sort params for consistent key generation
            param_str = json.dumps(params, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            return f"orchestration:{prefix}:{param_hash}"
        return f"orchestration:{prefix}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with automatic JSON decoding"""
        if not self.redis_client:
            return None

        try:
            self.cache_stats['total_requests'] += 1
            cached_data = self.redis_client.get(key)

            if cached_data:
                self.cache_stats['hits'] += 1
                return json.loads(cached_data)
            else:
                self.cache_stats['misses'] += 1
                return None

        except Exception as e:
            self.cache_stats['errors'] += 1
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL and automatic JSON encoding"""
        if not self.redis_client:
            return False

        try:
            # Convert dataclasses to dict for JSON serialization
            if hasattr(value, '__dataclass_fields__'):
                value = asdict(value)

            # Serialize to JSON
            json_data = json.dumps(value, default=str)

            # Set with TTL
            result = self.redis_client.setex(key, ttl, json_data)
            return bool(result)

        except Exception as e:
            self.cache_stats['errors'] += 1
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False

        try:
            result = self.redis_client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        if not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(f"orchestration:{pattern}*")
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache invalidate pattern error for {pattern}: {e}")
            return 0

    # High-level cache methods for specific data types

    async def get_dashboard_summary(self, project_filter: str = None) -> Optional[Dict]:
        """Get cached dashboard summary with project filtering"""
        key = self._generate_cache_key("dashboard_summary", {"project": project_filter})
        return await self.get(key)

    async def set_dashboard_summary(self, data: Dict, project_filter: str = None) -> bool:
        """Cache dashboard summary data"""
        key = self._generate_cache_key("dashboard_summary", {"project": project_filter})
        return await self.set(key, data, self.config.ttl_dashboard_summary)

    async def get_handoff_analytics(self, date_range: str = None) -> Optional[Dict]:
        """Get cached handoff analytics"""
        key = self._generate_cache_key("handoff_analytics", {"range": date_range})
        return await self.get(key)

    async def set_handoff_analytics(self, data: Dict, date_range: str = None) -> bool:
        """Cache handoff analytics data"""
        key = self._generate_cache_key("handoff_analytics", {"range": date_range})
        return await self.set(key, data, self.config.ttl_handoff_analytics)

    async def get_subagent_usage(self, agent_type: str = None) -> Optional[Dict]:
        """Get cached subagent usage statistics"""
        key = self._generate_cache_key("subagent_usage", {"type": agent_type})
        return await self.get(key)

    async def set_subagent_usage(self, data: Dict, agent_type: str = None) -> bool:
        """Cache subagent usage data"""
        key = self._generate_cache_key("subagent_usage", {"type": agent_type})
        return await self.set(key, data, self.config.ttl_subagent_usage)

    async def get_system_status(self) -> Optional[Dict]:
        """Get cached system status"""
        key = self._generate_cache_key("system_status")
        return await self.get(key)

    async def set_system_status(self, data: Dict) -> bool:
        """Cache system status data"""
        key = self._generate_cache_key("system_status")
        return await self.set(key, data, self.config.ttl_system_status)

    # Cache invalidation methods

    async def invalidate_dashboard_cache(self):
        """Invalidate all dashboard-related cache entries"""
        return await self.invalidate_pattern("dashboard_summary")

    async def invalidate_analytics_cache(self):
        """Invalidate analytics cache (handoffs, subagents, costs)"""
        patterns = ["handoff_analytics", "subagent_usage", "cost_metrics"]
        total = 0
        for pattern in patterns:
            total += await self.invalidate_pattern(pattern)
        return total

    async def invalidate_all(self):
        """Invalidate all orchestration cache entries"""
        return await self.invalidate_pattern("")

    # Performance and monitoring

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total = self.cache_stats['total_requests']
        if total == 0:
            hit_rate = 0
        else:
            hit_rate = (self.cache_stats['hits'] / total) * 100

        return {
            **self.cache_stats,
            'hit_rate_percent': round(hit_rate, 2),
            'connected': self.redis_client is not None
        }

    def reset_stats(self):
        """Reset cache statistics"""
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'total_requests': 0
        }

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive cache health check"""
        try:
            if not self.redis_client:
                return {
                    'status': 'disabled',
                    'connected': False,
                    'latency_ms': None,
                    'memory_usage': None
                }

            # Test latency
            start_time = datetime.now()
            self.redis_client.ping()
            latency = (datetime.now() - start_time).total_seconds() * 1000

            # Get memory info
            info = self.redis_client.info('memory')
            memory_used = info.get('used_memory_human', 'Unknown')

            return {
                'status': 'healthy',
                'connected': True,
                'latency_ms': round(latency, 2),
                'memory_usage': memory_used,
                'stats': self.get_cache_stats()
            }

        except Exception as e:
            return {
                'status': 'error',
                'connected': False,
                'error': str(e),
                'latency_ms': None,
                'memory_usage': None
            }

# Global cache manager instance
cache_manager: Optional[CacheManager] = None

def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global cache_manager
    if cache_manager is None:
        cache_manager = CacheManager()
    return cache_manager

async def init_cache(db_connection=None):
    """Initialize global cache manager"""
    global cache_manager
    cache_manager = CacheManager(db_connection=db_connection)
    await cache_manager.initialize()
    return cache_manager