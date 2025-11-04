from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from rag_service import RAGService
import os

app = FastAPI(title="Simple RAG API", version="1.0.0")

# Initialize RAG service
rag_service = RAGService()

class QueryRequest(BaseModel):
    query: str
    max_chunks: Optional[int] = 3

class QueryResponse(BaseModel):
    answer: str
    relevant_chunks: list[str]

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
        "message": "Simple RAG API with Ollama",
        "endpoints": {
            "query": "/query",
            "health": "/health"
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
    Query the RAG system with a question
    """
    try:
        if not rag_service.is_loaded():
            raise HTTPException(status_code=503, detail="RAG service not initialized")
        
        answer, relevant_chunks = rag_service.query(request.query, max_chunks=request.max_chunks)
        
        return QueryResponse(
            answer=answer,
            relevant_chunks=relevant_chunks
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

