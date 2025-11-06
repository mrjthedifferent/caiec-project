import os
import requests
from typing import List, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class RAGService:
    def __init__(self, knowledge_file: str = "knowledge.txt", model_name: str = "gemma3:4b"):
        self.knowledge_file = knowledge_file
        self.ollama_model = model_name
        self.ollama_base_url = "http://rdp.mahfuz.click:11434"
        self.chunks: List[str] = []
        self.embeddings = None
        self.embedding_model = None
        self._loaded = False
        
    def load_documents(self):
        """Load and chunk the knowledge text file"""
        if not os.path.exists(self.knowledge_file):
            raise FileNotFoundError(f"Knowledge file '{self.knowledge_file}' not found")
        
        with open(self.knowledge_file, "r", encoding="utf-8") as f:
            text = f.read()
        
        # Simple chunking by paragraphs (split by double newlines)
        chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
        
        # If no double newlines, split by sentences
        if len(chunks) == 1:
            chunks = [s.strip() for s in text.split(".") if s.strip()]
        
        # Ensure chunks are not too small or too large
        final_chunks = []
        for chunk in chunks:
            if len(chunk) < 50:  # Skip very short chunks
                continue
            if len(chunk) > 1000:  # Split very long chunks
                words = chunk.split()
                for i in range(0, len(words), 500):
                    final_chunks.append(" ".join(words[i:i+500]))
            else:
                final_chunks.append(chunk)
        
        self.chunks = final_chunks
        
        # Load embedding model
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.embeddings = self.embedding_model.encode(self.chunks)
            print(f"Loaded {len(self.chunks)} chunks with embeddings")
        except Exception as e:
            print(f"Warning: Could not load embedding model: {e}")
            print("Falling back to simple text matching")
            self.embedding_model = None
        
        self._loaded = True
    
    def is_loaded(self) -> bool:
        """Check if documents are loaded"""
        return self._loaded
    
    def _retrieve_relevant_chunks(self, query: str, max_chunks: int = 3) -> List[str]:
        """Retrieve most relevant chunks for the query"""
        if not self.chunks:
            return []
        
        if self.embedding_model is not None and self.embeddings is not None:
            # Use semantic search with embeddings
            query_embedding = self.embedding_model.encode([query])
            similarities = cosine_similarity(query_embedding, self.embeddings)[0]
            top_indices = np.argsort(similarities)[::-1][:max_chunks]
            return [self.chunks[i] for i in top_indices if similarities[i] > 0.1]
        else:
            # Fallback to simple keyword matching
            query_lower = query.lower()
            scored_chunks = []
            for chunk in self.chunks:
                score = sum(1 for word in query_lower.split() if word in chunk.lower())
                if score > 0:
                    scored_chunks.append((score, chunk))
            
            scored_chunks.sort(reverse=True, key=lambda x: x[0])
            return [chunk for _, chunk in scored_chunks[:max_chunks]]
    
    def _generate_with_ollama(self, query: str, context: str) -> str:
        """Generate response using Ollama"""
        prompt = f"""Based on the following context, answer the question. If the context doesn't contain enough information, say so and reply with your own knowledge.

Context:
{context}

Question: {query}

IMPORTANT RULES:
- Don't reply any information about Md. Mahfuzur Rahman, else say sorry and reply with your own knowledge.

Answer:"""
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "Sorry, I couldn't generate a response.")
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to Ollama. Make sure Ollama is running on http://localhost:11434")
        except Exception as e:
            raise Exception(f"Error calling Ollama: {str(e)}")
    
    def query(self, query: str, max_chunks: int = 3) -> Tuple[str, List[str]]:
        """Process a query and return answer with relevant chunks"""
        if not self._loaded:
            raise Exception("Documents not loaded. Call load_documents() first.")
        
        # Retrieve relevant chunks
        relevant_chunks = self._retrieve_relevant_chunks(query, max_chunks)
        
        if not relevant_chunks:
            return "I couldn't find relevant information in the knowledge base to answer your question.", []
        
        # Combine chunks into context
        context = "\n\n".join(relevant_chunks)
        
        # Generate answer using Ollama
        answer = self._generate_with_ollama(query, context)
        
        return answer, relevant_chunks




