"""RAG (Retrieval-Augmented Generation) service."""

from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from loguru import logger

from app.config import settings
from app.services.cache_service import CacheService
from app.services.embedding_service import EmbeddingService


# RAG Configuration - Tunable per document type
CHUNK_SIZE = 500      # tokens - increase for technical docs, decrease for FAQs
CHUNK_OVERLAP = 50    # tokens - 10% overlap recommended minimum
TOP_K = 5             # retrieval count - balance relevance vs context length
VECTOR_SIZE = 1536    # OpenAI text-embedding-3-small dimension


class RAGService:
    """Service for RAG-based question answering."""

    def __init__(self) -> None:
        """Initialize RAG service with required components."""
        self.embeddings = EmbeddingService()
        self.cache = CacheService()
        
        # Initialize Qdrant client
        self.qdrant = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        
        # Ensure collection exists
        self._ensure_collection()
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.7,
        )
        
        # Session memories - simple dict storing last k exchanges (in production, use Redis)
        self._memories: dict[str, list[dict[str, str]]] = {}
        self._memory_window = 5  # Keep last 5 exchanges
        
        # System prompt for RAG
        self.system_prompt = """You are NerdsIQ, a helpful AI assistant for NerdsToGo staff.
Answer questions based on the provided context from company documents.
If the context doesn't contain relevant information, say so clearly but still try to be helpful.
Always be professional, concise, and helpful.

Context from documents:
{context}

Previous conversation:
{history}
"""

    def _ensure_collection(self) -> None:
        """Ensure the Qdrant collection exists, create if not."""
        collections = self.qdrant.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if settings.qdrant_collection not in collection_names:
            logger.info(f"Creating Qdrant collection: {settings.qdrant_collection}")
            self.qdrant.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Collection {settings.qdrant_collection} created")

    def _get_memory(self, session_id: str) -> list[dict[str, str]]:
        """Get conversation memory for a session."""
        if session_id not in self._memories:
            self._memories[session_id] = []
        return self._memories[session_id]

    def _add_to_memory(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        """Add an exchange to session memory, keeping only last k exchanges."""
        memory = self._get_memory(session_id)
        memory.append({"user": user_msg, "assistant": assistant_msg})
        # Keep only last k exchanges
        if len(memory) > self._memory_window:
            self._memories[session_id] = memory[-self._memory_window:]

    async def query(
        self,
        question: str,
        session_id: str,
    ) -> tuple[str, list[str]]:
        """
        Process a RAG query.
        
        Args:
            question: User's question
            session_id: Session ID for conversation continuity
            
        Returns:
            Tuple of (answer, list of source URLs)
        """
        # Step 1: Check cache
        cache_key = self.cache.generate_key(question)
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for query: {question[:50]}...")
            return cached["answer"], cached["sources"]
        
        # Step 2: Generate embedding for question
        question_embedding = await self.embeddings.embed_text(question)
        
        # Step 3: Search Qdrant for relevant chunks
        search_results = self.qdrant.query_points(
            collection_name=settings.qdrant_collection,
            query=question_embedding,
            limit=TOP_K,
        ).points
        
        # Step 4: Build context from retrieved chunks
        context_parts = []
        sources = []
        
        for result in search_results:
            payload = result.payload or {}
            text = payload.get("text", "")
            source_url = payload.get("source_url", "")
            source_name = payload.get("source_name", "Unknown")
            
            context_parts.append(f"[From: {source_name}]\n{text}")
            if source_url and source_url not in sources:
                sources.append(source_url)
        
        context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found."
        
        # Step 5: Get conversation history
        memory = self._get_memory(session_id)
        history_text = self._format_history(memory)
        
        # Step 6: Query LLM
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{question}"),
        ])
        
        chain = prompt | self.llm
        response = await chain.ainvoke({
            "context": context,
            "history": history_text,
            "question": question,
        })
        
        answer = response.content
        
        # Step 7: Update memory
        self._add_to_memory(session_id, question, answer)
        
        # Step 8: Cache the result
        await self.cache.set(cache_key, {"answer": answer, "sources": sources})
        
        logger.info(f"RAG query processed: {question[:50]}... -> {len(sources)} sources")
        
        return answer, sources

    def _format_history(self, memory: list[dict[str, str]]) -> str:
        """Format conversation history for prompt."""
        if not memory:
            return "No previous conversation."
        
        formatted = []
        for exchange in memory:
            formatted.append(f"User: {exchange['user']}")
            formatted.append(f"Assistant: {exchange['assistant']}")
        
        return "\n".join(formatted)

    def clear_session(self, session_id: str) -> None:
        """Clear conversation memory for a session."""
        if session_id in self._memories:
            del self._memories[session_id]
            logger.info(f"Cleared memory for session: {session_id}")
