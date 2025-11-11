import os
import requests
import re
import json
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from db_utils import DatabaseManager
from multi_agent import MultiAgentSystem

class RAGService:
    def __init__(self, knowledge_file: str = "knowledge.txt", model_name: str = "gemma3:4b", 
                 use_database: bool = True):
        self.knowledge_file = knowledge_file
        self.ollama_model = model_name
        self.ollama_base_url = "http://rdp.mahfuz.click:11434"
        self.chunks: List[str] = []
        self.embeddings = None
        self.embedding_model = None
        self._loaded = False
        self.use_database = use_database
        self.db_manager = None
        self.multi_agent = None
        
        if use_database:
            try:
                self.db_manager = DatabaseManager()
                if self.db_manager.connect():
                    print("Database connection established")
                    # Initialize multi-agent system with database tools
                    self.multi_agent = MultiAgentSystem(
                        ollama_base_url=self.ollama_base_url,
                        model_name=self.ollama_model,
                        db_manager=self.db_manager
                    )
                    print("Multi-agent system initialized with database tools")
                else:
                    print("Warning: Could not connect to database. Database queries will be disabled.")
                    self.use_database = False
            except Exception as e:
                print(f"Warning: Database initialization failed: {e}. Database queries will be disabled.")
                self.use_database = False
        
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
        prompt = f"""Based on the following context which is a employee knowledge base, answer the question. If the context doesn't contain enough information, say so.

Context:
{context}

Question: {query}

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
    
    def _extract_employee_id(self, query: str) -> Optional[str]:
        """Extract employee ID from query (e.g., EMP001, userId EMP002, etc.)"""
        # Pattern to match employee IDs like EMP001, EMP002, etc.
        patterns = [
            r'\b(EMP\d{3,})\b',  # EMP001, EMP002, etc.
            r'\buserId\s+(EMP\d{3,})\b',  # userId EMP001
            r'\bemployee\s+id\s+(EMP\d{3,})\b',  # employee id EMP001
            r'\bID\s+(EMP\d{3,})\b',  # ID EMP001
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    def _query_database(self, employee_id: str) -> Optional[str]:
        """Query database for employee information"""
        if not self.use_database or not self.db_manager:
            return None
        
        try:
            employee = self.db_manager.get_employee_by_id(employee_id)
            if employee:
                # Format employee data as context
                context = f"""Employee Information:
EmployeeID: {employee.get('EmployeeID', 'N/A')}
Name: {employee.get('Name', 'N/A')}
Email: {employee.get('Email', 'N/A')}
Phone: {employee.get('Phone', 'N/A')}
Department: {employee.get('Department', 'N/A')}
Position: {employee.get('Position', 'N/A')}
Join Date: {employee.get('JoinDate', 'N/A')}
Salary (USD): {employee.get('SalaryUSD', 'N/A')}"""
                return context
        except Exception as e:
            print(f"Error querying database: {e}")
        
        return None
    
    def query(self, query: str, max_chunks: int = 3, use_multi_agent: bool = True) -> Tuple[str, List[str]]:
        """
        Process a query using multi-agent system (LLM decides when to call database)
        If use_multi_agent is False, falls back to traditional RAG
        """
        if not self._loaded:
            raise Exception("Documents not loaded. Call load_documents() first.")
        
        # Use multi-agent system if available and enabled
        if use_multi_agent and self.multi_agent and self.use_database:
            # Get relevant chunks from knowledge base for context
            relevant_chunks = self._retrieve_relevant_chunks(query, max_chunks)
            context = "\n\n".join(relevant_chunks) if relevant_chunks else None
            
            # Let the multi-agent system handle the query
            # The LLM will decide if it needs to call database tools
            answer, tool_calls = self.multi_agent.query(query, context)
            
            # Format relevant chunks to include tool call results
            formatted_chunks = relevant_chunks.copy() if relevant_chunks else []
            for tool_call in tool_calls:
                tool_result = self._format_tool_result_for_chunks(tool_call)
                if tool_result:
                    formatted_chunks.append(tool_result)
            
            return answer, formatted_chunks
        
        # Fallback to traditional RAG (for backward compatibility)
        # Check if query contains an employee ID
        employee_id = self._extract_employee_id(query)
        
        if employee_id and self.use_database:
            # Query database for employee information
            db_context = self._query_database(employee_id)
            
            if db_context:
                # Use database context for the answer
                answer = self._generate_with_ollama(query, db_context)
                return answer, [db_context]
            else:
                # Employee ID not found in database, try regular search
                relevant_chunks = self._retrieve_relevant_chunks(query, max_chunks)
                if not relevant_chunks:
                    return f"I couldn't find information for employee ID {employee_id} in the database.", []
                context = "\n\n".join(relevant_chunks)
                answer = self._generate_with_ollama(query, context)
                return answer, relevant_chunks
        
        # Regular query processing
        relevant_chunks = self._retrieve_relevant_chunks(query, max_chunks)
        
        if not relevant_chunks:
            return "I couldn't find relevant information in the knowledge base to answer your question.", []
        
        # Combine chunks into context
        context = "\n\n".join(relevant_chunks)
        
        # Generate answer using Ollama
        answer = self._generate_with_ollama(query, context)
        
        return answer, relevant_chunks
    
    def _format_tool_result_for_chunks(self, tool_call: dict) -> Optional[str]:
        """Format tool call result for chunks display"""
        tool_name = tool_call.get("tool", "")
        result = tool_call.get("result", {})
        
        if isinstance(result, dict) and result.get("success"):
            data = result.get("data", [])
            if isinstance(data, list) and len(data) > 0:
                if len(data) == 1:
                    emp = data[0]
                    return f"Database Query Result - {tool_name}:\nEmployeeID: {emp.get('EmployeeID')}, Name: {emp.get('Name')}, Department: {emp.get('Department')}, Position: {emp.get('Position')}"
                else:
                    return f"Database Query Result - {tool_name}: Found {len(data)} employees"
            elif isinstance(data, dict):
                return f"Database Query Result - {tool_name}:\n{json.dumps(data, indent=2, default=str)}"
        
        return None
    
    def query_by_employee_id(self, employee_id: str) -> Tuple[str, Optional[dict]]:
        """Query employee information directly by employee ID"""
        if not self.use_database or not self.db_manager:
            return "Database is not available.", None
        
        try:
            employee = self.db_manager.get_employee_by_id(employee_id.upper())
            if employee:
                # Format employee data
                context = f"""Employee Information:
EmployeeID: {employee.get('EmployeeID', 'N/A')}
Name: {employee.get('Name', 'N/A')}
Email: {employee.get('Email', 'N/A')}
Phone: {employee.get('Phone', 'N/A')}
Department: {employee.get('Department', 'N/A')}
Position: {employee.get('Position', 'N/A')}
Join Date: {employee.get('JoinDate', 'N/A')}
Salary (USD): {employee.get('SalaryUSD', 'N/A')}"""
                
                # Generate a natural language response
                query_text = f"Tell me about employee {employee_id}"
                answer = self._generate_with_ollama(query_text, context)
                return answer, employee
            else:
                return f"Employee with ID {employee_id} not found in the database.", None
        except Exception as e:
            return f"Error querying database: {str(e)}", None




