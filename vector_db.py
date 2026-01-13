import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional

# Initialize embedding model (loaded lazily on first use)
_embedding_model = None
_chroma_client = None
_collection = None

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "memories"
CHROMA_PERSIST_DIR = "./chroma_db"


def get_embedding_model() -> SentenceTransformer:
    """Get or initialize the embedding model (lazy loading)"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def get_collection():
    """Get or initialize the ChromaDB collection"""
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def init_vector_db():
    """Initialize the vector database on startup"""
    collection = get_collection()
    print(f"Vector DB initialized with {collection.count()} documents")
    return collection


def get_embedding(text: str) -> List[float]:
    """Generate embedding for a text string"""
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def add_to_vector_db(
    memory_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Add a document to the vector database with its embedding"""
    collection = get_collection()
    embedding = get_embedding(content)

    # ChromaDB metadata must be flat (no nested dicts/lists)
    flat_metadata = {}
    if metadata:
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                flat_metadata[key] = value
            elif isinstance(value, list):
                flat_metadata[key] = ",".join(str(v) for v in value)

    collection.add(
        ids=[memory_id],
        embeddings=[embedding],
        documents=[content],
        metadatas=[flat_metadata] if flat_metadata else None
    )


def search_vector_db(
    query: str,
    limit: int = 5,
    type_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search for similar documents using semantic similarity"""
    collection = get_collection()
    query_embedding = get_embedding(query)

    # Build where clause for filtering
    where = None
    if type_filter:
        where = {"type": type_filter}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=limit,
        where=where,
        include=["documents", "metadatas", "distances"]
    )

    # Transform results into a list of dicts
    items = []
    if results and results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            # Convert comma-separated tags back to list
            tags = metadata.get("tags", "")
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            items.append({
                "id": doc_id,
                "content": results["documents"][0][i],
                "type": metadata.get("type", "semantic"),
                "tags": tags,
                "source": metadata.get("source", "manual"),
                "confidence": metadata.get("confidence", 0.8),
                "created_at": metadata.get("created_at", ""),
                "similarity": 1 - results["distances"][0][i]  # Convert distance to similarity
            })

    return items


def delete_from_vector_db(memory_id: str) -> bool:
    """Delete a document from the vector database"""
    collection = get_collection()
    try:
        collection.delete(ids=[memory_id])
        return True
    except Exception:
        return False
