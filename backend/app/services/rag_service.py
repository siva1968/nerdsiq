"""RAG (Retrieval-Augmented Generation) service."""

import asyncio
from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, Filter, FieldCondition, MatchText
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import RateLimitError

from app.config import settings
from app.services.cache_service import CacheService
from app.services.embedding_service import EmbeddingService


# RAG Configuration - Tunable per document type
CHUNK_SIZE = 500      # tokens - increase for technical docs, decrease for FAQs
CHUNK_OVERLAP = 50    # tokens - 10% overlap recommended minimum
TOP_K = 8             # retrieval count - increased from 5 for better coverage
TOP_K_TITLE = 3       # additional results from title matching
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
        
        # Initialize LLM with rate limiting
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.7,
            request_timeout=30,  # 30 second timeout
            max_retries=3,
        )
        
        # Session memories - simple dict storing last k exchanges (in production, use Redis)
        self._memories: dict[str, list[dict[str, str]]] = {}
        self._memory_window = 5  # Keep last 5 exchanges
        
        # System prompt for RAG
        self.system_prompt = """You are NerdsIQ, a helpful AI assistant for NerdsToGo staff.
Your job is to answer questions using the company documents provided in the context below.

RULES:
1. ALWAYS provide an answer based on what IS in the context - focus on what you CAN share
2. Format procedures as numbered steps for clarity
3. Use **bold** for key terms, menu items, and important points
4. If the context has related information but not the exact answer, share the related info and explain how it might help
5. NEVER start with "The context does not contain" or similar negative phrases
6. Be direct and helpful - users are employees who need practical guidance

Context from documents:
{context}

Previous conversation:
{history}
"""
        
        # Query expansion prompt
        self.query_expansion_prompt = """Given the user's question, generate an expanded search query that includes:
1. The original question terms
2. Related synonyms and alternative phrasings
3. Likely document titles or topics that might contain the answer

User question: {question}

Return ONLY the expanded search query (no explanation), optimized for semantic search:"""

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
        model: str | None = None,
    ) -> tuple[str, list[str]]:
        """
        Process a RAG query.
        
        Args:
            question: User's question
            session_id: Session ID for conversation continuity
            model: Optional OpenAI model override (e.g., gpt-4o, gpt-4o-mini)
            
        Returns:
            Tuple of (answer, list of source URLs)
        """
        # Step 1: Check cache
        cache_key = self.cache.generate_key(question)
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for query: {question[:50]}...")
            return cached["answer"], cached["sources"]
        
        # Step 2: Expand the query for better retrieval
        expanded_query = await self._expand_query(question)
        logger.debug(f"Expanded query: {expanded_query[:100]}...")
        
        # Step 3: Generate embedding for expanded question
        question_embedding = await self.embeddings.embed_text(expanded_query)
        
        # Step 4: Search Qdrant for relevant chunks (semantic search)
        # Using search() for Qdrant client 1.7.3 compatibility
        search_results = self.qdrant.search(
            collection_name=settings.qdrant_collection,
            query_vector=question_embedding,
            limit=TOP_K,
            with_payload=True,
        )
        
        # Step 5: Secondary search - title/filename matching
        title_results = await self._search_by_title(question)
        
        # Step 6: Merge and deduplicate results
        all_results = self._merge_results(search_results, title_results)
        
        # Step 7: Build context from retrieved chunks
        context_parts = []
        sources = []
        source_map = {}  # Track unique sources by URL
        
        for result in all_results:
            payload = result.payload or {}
            text = payload.get("text", "")
            source_url = payload.get("source_url", "")
            source_name = payload.get("source_name", "Unknown")
            
            context_parts.append(f"[From: {source_name}]\n{text}")
            if source_url and source_url not in source_map:
                source_map[source_url] = source_name
                sources.append({"url": source_url, "name": source_name})
        
        context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found."
        
        # Step 8: Get conversation history
        memory = self._get_memory(session_id)
        history_text = self._format_history(memory)
        
        # Step 9: Query LLM (use override model if provided)
        llm_to_use = self.llm
        if model:
            llm_to_use = ChatOpenAI(
                model=model,
                api_key=settings.openai_api_key,
                temperature=0.7,
            )
            logger.info(f"Using override model: {model}")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{question}"),
        ])
        
        chain = prompt | llm_to_use
        response = await chain.ainvoke({
            "context": context,
            "history": history_text,
            "question": question,
        })
        
        answer = response.content
        
        # Step 10: Update memory
        self._add_to_memory(session_id, question, answer)
        
        # Step 11: Cache the result
        await self.cache.set(cache_key, {"answer": answer, "sources": sources})
        
        logger.info(f"RAG query processed: {question[:50]}... -> {len(sources)} sources, {len(all_results)} chunks")
        
        return answer, sources

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((RateLimitError, Exception))
    )
    async def _expand_query(self, question: str) -> str:
        """
        Expand the user's query with synonyms and related terms for better retrieval.
        
        Uses LLM to rewrite the question with additional context terms.
        """
        try:
            # Use a fast, cheap model call for query expansion
            expansion_llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.openai_api_key,
                temperature=0.3,
                max_tokens=150,
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("human", self.query_expansion_prompt),
            ])
            
            chain = prompt | expansion_llm
            response = await chain.ainvoke({"question": question})
            
            expanded = response.content.strip()
            
            # Combine original question with expanded version for best results
            return f"{question} {expanded}"
            
        except Exception as e:
            logger.warning(f"Query expansion failed, using original: {e}")
            return question

    async def _search_by_title(self, question: str) -> list:
        """
        Search for documents by title/filename matching.
        
        Extracts key terms from the question and matches against source_name field.
        """
        try:
            # Extract potential document name keywords
            keywords = self._extract_keywords(question)
            
            if not keywords:
                return []
            
            title_results = []
            seen_ids = set()
            
            for keyword in keywords[:3]:  # Limit to top 3 keywords
                # Scroll through collection looking for title matches
                results = self.qdrant.scroll(
                    collection_name=settings.qdrant_collection,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="source_name",
                                match=MatchText(text=keyword),
                            )
                        ]
                    ),
                    limit=TOP_K_TITLE,
                    with_payload=True,
                    with_vectors=False,
                )
                
                for point in results[0]:
                    if point.id not in seen_ids:
                        seen_ids.add(point.id)
                        title_results.append(point)
                        
                        if len(title_results) >= TOP_K_TITLE:
                            break
                
                if len(title_results) >= TOP_K_TITLE:
                    break
            
            if title_results:
                logger.debug(f"Title search found {len(title_results)} results for: {keywords}")
            
            return title_results
            
        except Exception as e:
            logger.warning(f"Title search failed: {e}")
            return []

    def _extract_keywords(self, question: str) -> list[str]:
        """Extract potential document name keywords from a question."""
        # Common words to exclude
        stopwords = {
            'what', 'how', 'why', 'when', 'where', 'who', 'which', 'is', 'are', 
            'was', 'were', 'do', 'does', 'did', 'can', 'could', 'would', 'should',
            'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'under', 'again', 'further', 'then', 'once',
            'i', 'me', 'my', 'we', 'our', 'you', 'your', 'it', 'its', 'this', 'that',
            'and', 'but', 'or', 'if', 'because', 'as', 'until', 'while', 'there',
            'new', 'work', 'get', 'set', 'use', 'make', 'find', 'help', 'need',
        }
        
        # Extract words that might be document names
        words = question.lower().split()
        keywords = []
        
        for word in words:
            # Clean the word
            clean_word = ''.join(c for c in word if c.isalnum())
            
            if clean_word and clean_word not in stopwords and len(clean_word) > 2:
                keywords.append(clean_word)
        
        # Also look for multi-word terms (e.g., "ConnectWise", "RingCentral")
        common_terms = [
            'connectwise', 'ringcentral', 'linkedin', 'facebook', 'google',
            'invoice', 'ticket', 'customer', 'client', 'msp', 'sop',
            'onboarding', 'diagnostic', 'pricing', 'credit', 'memo',
            'vpn', 'nordvpn', 'wisepay', 'pci', 'qdrant', 'outlook',
        ]
        
        question_lower = question.lower()
        for term in common_terms:
            if term in question_lower and term not in keywords:
                keywords.insert(0, term)  # Prioritize known terms
        
        return keywords

    def _merge_results(self, semantic_results: list, title_results: list) -> list:
        """Merge semantic search and title search results, removing duplicates."""
        seen_texts = set()
        merged = []
        
        # Add semantic results first (higher priority)
        for result in semantic_results:
            text = (result.payload or {}).get("text", "")[:100]  # Use first 100 chars as key
            if text not in seen_texts:
                seen_texts.add(text)
                merged.append(result)
        
        # Add title results that aren't duplicates
        for result in title_results:
            text = (result.payload or {}).get("text", "")[:100]
            if text not in seen_texts:
                seen_texts.add(text)
                merged.append(result)
        
        return merged

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
