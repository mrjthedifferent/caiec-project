from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from rag_service import RAGService
import os

app = FastAPI(title="Simple RAG API", version="1.0.0")

# Initialize RAG service with database support
rag_service = RAGService(use_database=True)

class QueryRequest(BaseModel):
    query: str
    max_chunks: Optional[int] = 3

class QueryResponse(BaseModel):
    answer: str
    relevant_chunks: list[str]
    tool_calls_used: Optional[bool] = False  # Indicates if multi-agent system used tools

class EmployeeResponse(BaseModel):
    answer: str
    employee_data: Optional[dict] = None

@app.on_event("startup")
async def startup_event():
    """Initialize RAG service on startup"""
    try:
        rag_service.load_documents()
        print("RAG service initialized successfully")
    except Exception as e:
        print(f"Error initializing RAG service: {e}")

@app.get("/")
async def root():
    return {
        "message": "Multi-Agent RAG API with Ollama and MySQL Database",
        "description": "The LLM agent can automatically call database tools when needed",
        "endpoints": {
            "query": "/query - Query with automatic tool calling",
            "employee": "/employee/{employee_id} - Direct employee lookup",
            "health": "/health - Health check",
            "reload": "/reload - Reload documents"
        },
        "features": {
            "multi_agent": "LLM decides when to query database",
            "tool_calling": "Automatic database tool invocation",
            "rag": "Retrieval Augmented Generation from knowledge base"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "documents_loaded": rag_service.is_loaded()
    }

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query the RAG system with a question.
    The LLM will automatically decide if it needs to query the database using available tools.
    """
    try:
        if not rag_service.is_loaded():
            raise HTTPException(status_code=503, detail="RAG service not initialized")
        
        # Use multi-agent system (LLM decides when to call database)
        answer, relevant_chunks = rag_service.query(
            request.query, 
            max_chunks=request.max_chunks,
            use_multi_agent=True
        )
        
        # Check if database tools were used (indicated by database query results in chunks)
        tool_calls_used = any("Database Query Result" in chunk for chunk in relevant_chunks)
        
        return QueryResponse(
            answer=answer,
            relevant_chunks=relevant_chunks,
            tool_calls_used=tool_calls_used
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.post("/reload")
async def reload_documents():
    """Reload documents from the knowledge file"""
    try:
        rag_service.load_documents()
        return {"message": "Documents reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reloading documents: {str(e)}")

@app.get("/employee/{employee_id}", response_model=EmployeeResponse)
async def get_employee_by_id(employee_id: str):
    """
    Get employee information by EmployeeID (e.g., EMP001, EMP002)
    """
    try:
        answer, employee_data = rag_service.query_by_employee_id(employee_id)
        return EmployeeResponse(
            answer=answer,
            employee_data=employee_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying employee: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

