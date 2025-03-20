import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

import redis
from sentence_transformers import SentenceTransformer

class RedisMemoryBackend:
    """Redis-based backend for storing and retrieving coding preferences.
    
    This backend uses Redis for storage and sentence-transformers for semantic search.
    It can be used as an alternative to mem0 when you don't have a mem0 account.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", embedding_model: str = "all-MiniLM-L6-v2"):
        """Initialize the Redis backend.
        
        Args:
            redis_url: Redis connection URL
            embedding_model: Name of the sentence-transformers model to use for embeddings
        """
        self.redis_client = redis.from_url(redis_url)
        self.model = SentenceTransformer(embedding_model)
        self.prefix = "coding_preference:"
        self.embedding_prefix = "embedding:"
        
    def add(self, messages: List[Dict[str, str]], user_id: str = "default_user", **kwargs) -> str:
        """Add a new coding preference to Redis.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            user_id: User identifier
            **kwargs: Additional arguments (ignored)
            
        Returns:
            ID of the stored preference
        """
        # Generate a unique ID for this preference
        preference_id = str(uuid.uuid4())
        key = f"{self.prefix}{user_id}:{preference_id}"
        
        # Extract content from messages
        content = "\n".join([msg["content"] for msg in messages])
        
        # Create memory object
        memory = {
            "id": preference_id,
            "user_id": user_id,
            "messages": messages,
            "content": content,
            "created_at": datetime.now().isoformat(),
        }
        
        # Store in Redis
        self.redis_client.set(key, json.dumps(memory))
        
        # Generate and store embedding
        embedding = self.model.encode(content).tolist()
        self.redis_client.set(f"{self.embedding_prefix}{key}", json.dumps(embedding))
        
        # Add to user's list of preferences
        self.redis_client.sadd(f"{self.prefix}{user_id}:ids", preference_id)
        
        return preference_id
    
    def get_all(self, user_id: str = "default_user", page: int = 1, page_size: int = 50, **kwargs) -> Dict[str, Any]:
        """Get all coding preferences for a user.
        
        Args:
            user_id: User identifier
            page: Page number (1-indexed)
            page_size: Number of items per page
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Dictionary with results and pagination info
        """
        # Get all preference IDs for this user
        preference_ids = self.redis_client.smembers(f"{self.prefix}{user_id}:ids")
        preference_ids = sorted(list(preference_ids))  # Sort for consistent ordering
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_ids = preference_ids[start_idx:end_idx]
        
        # Fetch all preferences
        results = []
        for pid in page_ids:
            key = f"{self.prefix}{user_id}:{pid.decode('utf-8')}"
            data = self.redis_client.get(key)
            if data:
                memory = json.loads(data)
                results.append({"memory": memory})
        
        return {
            "results": results,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": len(preference_ids),
                "total_pages": (len(preference_ids) + page_size - 1) // page_size
            }
        }
    
    def search(self, query: str, user_id: str = "default_user", limit: int = 5, **kwargs) -> Dict[str, Any]:
        """Search coding preferences using semantic search.
        
        Args:
            query: Search query
            user_id: User identifier
            limit: Maximum number of results to return
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Dictionary with search results
        """
        # Get all preference IDs for this user
        preference_ids = self.redis_client.smembers(f"{self.prefix}{user_id}:ids")
        
        if not preference_ids:
            return {"results": []}
        
        # Generate query embedding
        query_embedding = self.model.encode(query).tolist()
        
        # Fetch all preferences and their embeddings
        results = []
        for pid in preference_ids:
            pid_str = pid.decode('utf-8')
            key = f"{self.prefix}{user_id}:{pid_str}"
            embedding_key = f"{self.embedding_prefix}{key}"
            
            data = self.redis_client.get(key)
            embedding_data = self.redis_client.get(embedding_key)
            
            if data and embedding_data:
                memory = json.loads(data)
                embedding = json.loads(embedding_data)
                
                # Calculate similarity (dot product)
                similarity = sum(a * b for a, b in zip(query_embedding, embedding))
                
                results.append({
                    "memory": memory,
                    "similarity": similarity
                })
        
        # Sort by similarity (highest first) and limit results
        results.sort(key=lambda x: x["similarity"], reverse=True)
        results = results[:limit]
        
        # Format results to match mem0 API
        formatted_results = [{"memory": item["memory"]} for item in results]
        
        return {
            "results": formatted_results
        }