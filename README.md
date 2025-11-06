# Simple RAG API with FastAPI and Ollama

A simple Retrieval Augmented Generation (RAG) system built with FastAPI and Ollama. This project uses a local text file as a knowledge base and leverages Ollama's Llama model for generating contextual responses.

## Features

- 🚀 FastAPI-based REST API
- 📚 Document-based knowledge retrieval
- 🔍 Semantic search using embeddings
- 🤖 LLM-powered response generation via Ollama
- 📝 Simple text file-based knowledge base
- 🔄 Hot-reload documents without restarting

## Prerequisites

- Python 3.8 or higher
- Ollama installed and running
- Llama model pulled in Ollama

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install and Setup Ollama

1. Download Ollama from [https://ollama.ai](https://ollama.ai)
2. Install Ollama on your system
3. Pull the Llama model:
   ```bash
   ollama pull llama3.2
   ```
4. Ensure Ollama is running (default: `http://localhost:11434`)

### 3. Prepare Your Knowledge Base

Edit `knowledge.txt` with your own content. The file will be automatically chunked and indexed when the service starts.

## Usage

### Start the API Server

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### API Endpoints

#### `GET /`

Returns API information and available endpoints.

#### `GET /health`

Health check endpoint. Returns the status of the RAG service and whether documents are loaded.

**Response:**

```json
{
  "status": "healthy",
  "documents_loaded": true
}
```

#### `POST /query`

Query the RAG system with a question.

**Request Body:**

```json
{
  "query": "What is RAG?",
  "max_chunks": 3
}
```

**Response:**

```json
{
  "answer": "RAG (Retrieval Augmented Generation) is a technique...",
  "relevant_chunks": [
    "Retrieval Augmented Generation (RAG) is a technique...",
    "..."
  ]
}
```

**Parameters:**

- `query` (required): The question to ask
- `max_chunks` (optional): Maximum number of relevant chunks to retrieve (default: 3)

#### `POST /reload`

Reload documents from the knowledge file without restarting the server.

**Response:**

```json
{
  "message": "Documents reloaded successfully"
}
```

### Example Usage

#### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Query the RAG system
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?", "max_chunks": 3}'

# Reload documents
curl -X POST http://localhost:8000/reload
```

#### Using Python requests

```python
import requests

# Query example
response = requests.post(
    "http://localhost:8000/query",
    json={"query": "What is RAG?", "max_chunks": 3}
)
data = response.json()
print(data["answer"])
```

#### Using the Interactive API Docs

FastAPI provides automatic interactive API documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Configuration

### Changing the Ollama Model

Edit `main.py` and modify the `RAGService` initialization:

```python
rag_service = RAGService(model_name="your-model-name")
```

### Changing the Knowledge File

Edit `main.py` and modify the `RAGService` initialization:

```python
rag_service = RAGService(knowledge_file="your-file.txt")
```

### Changing Ollama URL

Edit `rag_service.py` and modify the `ollama_base_url` in the `__init__` method:

```python
self.ollama_base_url = "http://your-ollama-url:port"
```

## How It Works

1. **Document Loading**: On startup, the service loads `knowledge.txt` and splits it into chunks
2. **Embedding Generation**: Each chunk is converted to a vector embedding using SentenceTransformers
3. **Query Processing**: When a query is received:
   - The query is converted to an embedding
   - Similar chunks are retrieved using cosine similarity
   - The top N chunks are selected as context
4. **Response Generation**: The context and query are sent to Ollama, which generates a response

## Project Structure

```
.
├── main.py              # FastAPI application
├── rag_service.py       # RAG service implementation
├── knowledge.txt        # Knowledge base file
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Troubleshooting

### Ollama Connection Error

**Error**: `Could not connect to Ollama. Make sure Ollama is running on http://localhost:11434`

**Solution**:

- Ensure Ollama is installed and running
- Check if Ollama is accessible at `http://localhost:11434`
- Verify the model is pulled: `ollama list`

### Model Not Found

**Error**: `Error calling Ollama: model not found`

**Solution**: Pull the model in Ollama:

```bash
ollama pull llama3.2
```

### Knowledge File Not Found

**Error**: `Knowledge file 'knowledge.txt' not found`

**Solution**:

- Ensure `knowledge.txt` exists in the project directory
- Or update the `knowledge_file` parameter in `RAGService`

### Embedding Model Download Issues

The first run will download the SentenceTransformer model (`all-MiniLM-L6-v2`). This may take a few minutes and requires internet connection.

## Dependencies

- `fastapi`: Web framework for building APIs
- `uvicorn`: ASGI server
- `pydantic`: Data validation
- `requests`: HTTP library for Ollama API
- `sentence-transformers`: Embedding generation
- `scikit-learn`: Similarity calculations
- `numpy`: Numerical operations
- `torch`: PyTorch (required by sentence-transformers)

## License

This project is for training purposes as part of CAIEC project training.



