"""
Qdrant vector database management for SEC filing text chunks.
"""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest
)
from sentence_transformers import SentenceTransformer
import logging
import hashlib
from datetime import datetime

from config.settings import get_settings

logger = logging.getLogger(__name__)


class VectorDatabase:
    """Manages Qdrant vector database operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self.embedding_model = None
        self.collection_name = self.settings.qdrant.collection_name
        self._initialize()
    
    def _initialize(self):
        """Initialize Qdrant client and embedding model."""
        try:
            # Initialize Qdrant client
            self.client = QdrantClient(
                url=self.settings.qdrant.url,
                timeout=30.0
            )
            logger.info(f"Connected to Qdrant at {self.settings.qdrant.url}")
            
            # Load embedding model
            logger.info(f"Loading embedding model: {self.settings.app.embedding_model}")
            self.embedding_model = SentenceTransformer(
                self.settings.app.embedding_model
            )
            logger.info("Embedding model loaded successfully")
            
            # Create collection if it doesn't exist
            self._create_collection_if_not_exists()
            
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            raise
    
    def _create_collection_if_not_exists(self):
        """Create collection with proper configuration."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                # Get embedding dimension from model
                test_embedding = self.embedding_model.encode("test")
                vector_size = len(test_embedding)
                
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection '{self.collection_name}' with dimension {vector_size}")
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")
                
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise
    
    def _generate_chunk_id(self, text: str, metadata: Dict[str, Any]) -> str:
        """Generate deterministic ID for a text chunk."""
        content = f"{metadata.get('ticker', '')}_{metadata.get('section', '')}_{text[:100]}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        try:
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise
    
    def upsert_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """
        Insert or update documents in the vector database.
        
        Args:
            texts: List of text chunks
            metadatas: List of metadata dicts for each chunk
            batch_size: Number of documents to process at once
            
        Returns:
            Number of documents successfully upserted
        """
        if len(texts) != len(metadatas):
            raise ValueError("texts and metadatas must have the same length")
        
        total_upserted = 0
        
        try:
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]
                
                # Generate embeddings
                embeddings = self.embed_batch(batch_texts)
                
                # Create points
                points = []
                for text, embedding, metadata in zip(batch_texts, embeddings, batch_metadatas):
                    point_id = self._generate_chunk_id(text, metadata)
                    
                    payload = {
                        "text": text,
                        "ticker": metadata.get("ticker", ""),
                        "section": metadata.get("section", ""),
                        "fiscal_year": metadata.get("fiscal_year"),
                        "page": metadata.get("page"),
                        "chunk_index": metadata.get("chunk_index"),
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    points.append(
                        PointStruct(
                            id=point_id,
                            vector=embedding,
                            payload=payload
                        )
                    )
                
                # Upsert batch
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                
                total_upserted += len(points)
                logger.info(f"Upserted batch {i//batch_size + 1}: {len(points)} documents")
            
            logger.info(f"Successfully upserted {total_upserted} documents")
            return total_upserted
            
        except Exception as e:
            logger.error(f"Failed to upsert documents: {e}")
            raise
    
    def search(
        self,
        query: str,
        ticker: Optional[str] = None,
        section: Optional[str] = None,
        top_k: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Semantic search in the vector database.
        
        Args:
            query: Search query text
            ticker: Filter by company ticker
            section: Filter by document section
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            
        Returns:
            List of matching documents with scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embed_text(query)
            
            # Build filter
            filter_conditions = []
            if ticker:
                filter_conditions.append(
                    FieldCondition(
                        key="ticker",
                        match=MatchValue(value=ticker)
                    )
                )
            if section:
                filter_conditions.append(
                    FieldCondition(
                        key="section",
                        match=MatchValue(value=section)
                    )
                )
            
            query_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            # Perform search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=top_k,
                score_threshold=score_threshold
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "text": result.payload.get("text", ""),
                    "score": result.score,
                    "ticker": result.payload.get("ticker", ""),
                    "section": result.payload.get("section", ""),
                    "fiscal_year": result.payload.get("fiscal_year"),
                    "page": result.payload.get("page"),
                    "chunk_index": result.payload.get("chunk_index")
                })
            
            logger.info(f"Search returned {len(formatted_results)} results for query: '{query[:50]}'")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def hybrid_search(
        self,
        query: str,
        keywords: List[str],
        ticker: Optional[str] = None,
        section: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining semantic and keyword matching.
        
        Args:
            query: Semantic search query
            keywords: Keywords that must appear in results
            ticker: Filter by company ticker
            section: Filter by document section
            top_k: Number of results to return
            
        Returns:
            List of matching documents
        """
        try:
            # First do semantic search
            semantic_results = self.search(
                query=query,
                ticker=ticker,
                section=section,
                top_k=top_k * 2  # Get more candidates
            )
            
            # Filter by keywords
            filtered_results = []
            for result in semantic_results:
                text_lower = result["text"].lower()
                if any(keyword.lower() in text_lower for keyword in keywords):
                    filtered_results.append(result)
            
            # Return top_k results
            return filtered_results[:top_k]
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise
    
    def delete_by_ticker(self, ticker: str) -> bool:
        """Delete all documents for a specific ticker."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="ticker",
                            match=MatchValue(value=ticker)
                        )
                    ]
                )
            )
            logger.info(f"Deleted all documents for ticker: {ticker}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {}
    
    def health_check(self) -> bool:
        """Check if Qdrant is accessible."""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False


# Singleton instance
_vector_db: VectorDatabase = None


def get_vector_db() -> VectorDatabase:
    """Get vector database singleton."""
    global _vector_db
    if _vector_db is None:
        _vector_db = VectorDatabase()
    return _vector_db