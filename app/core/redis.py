"""
Redis configuration and client
"""
import redis.asyncio as redis
from typing import Optional, Any
import json
from app.core.config import settings


class RedisClient:
    """Redis client wrapper"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        if not self.client:
            self.client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
    
    async def ping(self) -> bool:
        """Test Redis connection"""
        if not self.client:
            await self.connect()
        return await self.client.ping()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if not self.client:
            await self.connect()
        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """Set value in Redis"""
        if not self.client:
            await self.connect()
        
        if not isinstance(value, str):
            value = json.dumps(value)
        
        if expire:
            return await self.client.setex(key, expire, value)
        return await self.client.set(key, value)
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.client:
            await self.connect()
        return await self.client.delete(key) > 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.client:
            await self.connect()
        return await self.client.exists(key) > 0


# Global Redis client instance
redis_client = RedisClient()


async def get_redis():
    """Get Redis client instance (for dependency injection)"""
    if not redis_client.client:
        await redis_client.connect()
    return redis_client.client
