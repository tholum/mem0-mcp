import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
from sqlalchemy import create_engine, Column, String, Text, DateTime, LargeBinary, Index, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sentence_transformers import SentenceTransformer

Base = declarative_base()

class CodingPreference(Base):
    """SQLAlchemy model for storing coding preferences."""
    
    __tablename__ = 'coding_preferences'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    messages = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime, nullable=False)
    
    # Create an index on user_id for faster lookups
    __table_args__ = (Index('idx_user_id', 'user_id'),)

class CodingPreferenceEmbedding(Base):
    """SQLAlchemy model for storing embeddings of coding preferences."""
    
    __tablename__ = 'coding_preference_embeddings'
    
    id = Column(String(36), primary_key=True)
    preference_id = Column(String(36), nullable=False, index=True)
    embedding = Column(LargeBinary, nullable=False)  # Serialized numpy array
    
    # Create an index on preference_id for faster lookups
    __table_args__ = (Index('idx_preference_id', 'preference_id'),)

class MySQLMemoryBackend:
    """MySQL-based backend for storing and retrieving coding preferences.
    
    This backend uses MySQL for storage and sentence-transformers for semantic search.
    It can be used as an alternative to mem0 when you don't have a mem0 account.
    """
    
    def __init__(self, mysql_url: str = "mysql+pymysql://root:password@localhost:3306/mem0_mcp", 
                 embedding_model: str = "all-MiniLM-L6-v2"):
        """Initialize the MySQL backend.
        
        Args:
            mysql_url: MySQL connection URL in SQLAlchemy format
            embedding_model: Name of the sentence-transformers model to use for embeddings
        """
        self.engine = create_engine(mysql_url)
        self.Session = sessionmaker(bind=self.engine)
        self.model = SentenceTransformer(embedding_model)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        
    def add(self, messages: List[Dict[str, str]], user_id: str = "default_user", **kwargs) -> str:
        """Add a new coding preference to MySQL.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            user_id: User identifier
            **kwargs: Additional arguments (ignored)
            
        Returns:
            ID of the stored preference
        """
        # Generate a unique ID for this preference
        preference_id = str(uuid.uuid4())
        
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
        
        # Generate embedding
        embedding = self.model.encode(content)
        
        # Store in MySQL
        with self.Session() as session:
            # Store preference
            preference = CodingPreference(
                id=preference_id,
                user_id=user_id,
                content=content,
                messages=json.dumps(messages),
                created_at=datetime.now()
            )
            session.add(preference)
            
            # Store embedding
            embedding_record = CodingPreferenceEmbedding(
                id=str(uuid.uuid4()),
                preference_id=preference_id,
                embedding=embedding.tobytes()
            )
            session.add(embedding_record)
            
            session.commit()
        
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
        with self.Session() as session:
            # Count total preferences for this user
            total = session.query(CodingPreference).filter(
                CodingPreference.user_id == user_id
            ).count()
            
            # Apply pagination
            offset = (page - 1) * page_size
            
            # Fetch preferences
            preferences = session.query(CodingPreference).filter(
                CodingPreference.user_id == user_id
            ).order_by(CodingPreference.created_at.desc()).offset(offset).limit(page_size).all()
            
            # Format results
            results = []
            for pref in preferences:
                memory = {
                    "id": pref.id,
                    "user_id": pref.user_id,
                    "messages": json.loads(pref.messages),
                    "content": pref.content,
                    "created_at": pref.created_at.isoformat(),
                }
                results.append({"memory": memory})
            
            return {
                "results": results,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": (total + page_size - 1) // page_size if total > 0 else 1
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
        # Generate query embedding
        query_embedding = self.model.encode(query)
        
        with self.Session() as session:
            # Get all preferences for this user
            preferences = session.query(CodingPreference).filter(
                CodingPreference.user_id == user_id
            ).all()
            
            if not preferences:
                return {"results": []}
            
            # Get all embeddings
            preference_ids = [pref.id for pref in preferences]
            embeddings = session.query(CodingPreferenceEmbedding).filter(
                CodingPreferenceEmbedding.preference_id.in_(preference_ids)
            ).all()
            
            # Create a mapping of preference_id to embedding
            embedding_map = {}
            for emb in embeddings:
                embedding_map[emb.preference_id] = np.frombuffer(emb.embedding, dtype=np.float32)
            
            # Calculate similarities and rank results
            results = []
            for pref in preferences:
                if pref.id in embedding_map:
                    embedding = embedding_map[pref.id]
                    # Calculate cosine similarity
                    similarity = np.dot(query_embedding, embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
                    )
                    
                    memory = {
                        "id": pref.id,
                        "user_id": pref.user_id,
                        "messages": json.loads(pref.messages),
                        "content": pref.content,
                        "created_at": pref.created_at.isoformat(),
                    }
                    
                    results.append({
                        "memory": memory,
                        "similarity": float(similarity)
                    })
            
            # Sort by similarity (highest first) and limit results
            results.sort(key=lambda x: x["similarity"], reverse=True)
            results = results[:limit]
            
            # Format results to match mem0 API
            formatted_results = [{"memory": item["memory"]} for item in results]
            
            return {
                "results": formatted_results
            }