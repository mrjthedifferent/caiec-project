# Multi-Agent System Guide

This system implements a **multi-agent architecture** where the LLM (Language Model) acts as an intelligent agent that can decide when to call database tools to answer user queries.

## How It Works

### Architecture Overview

```
User Query
    ↓
RAG Service (Retrieval from Knowledge Base)
    ↓
Multi-Agent System
    ↓
LLM Agent (Decides: Do I need database info?)
    ├─→ Yes → Call Database Tool → Get Results → Generate Answer
    └─→ No → Use Knowledge Base Context → Generate Answer
```

### Key Components

1. **Tool Registry** (`agent_tools.py`)
   - Defines available database tools/functions
   - Registers tools that the LLM can call
   - Executes tool calls and returns results

2. **Multi-Agent System** (`multi_agent.py`)
   - Implements ReAct-style reasoning
   - LLM decides when to call tools
   - Handles tool execution and result integration
   - Iterative conversation loop

3. **RAG Service** (`rag_service.py`)
   - Integrates multi-agent system
   - Provides knowledge base context
   - Combines RAG and tool calling

## Available Database Tools

The LLM can call these tools automatically:

### 1. `get_employee_by_id`
Get detailed information about a specific employee by their EmployeeID.

**When to use**: When user asks about a specific employee ID (e.g., EMP001, EMP002)

**Parameters**:
- `employee_id` (string, required): The employee ID (e.g., "EMP001")

**Example**: User asks "Tell me about EMP001"

### 2. `search_employees`
Search for employees by name, email, department, or partial employee ID.

**When to use**: When user asks about employees but doesn't provide a specific ID

**Parameters**:
- `search_term` (string, required): Search term
- `limit` (integer, optional): Max results (default: 10)

**Example**: User asks "Who works in IT Support?"

### 3. `get_employees_by_department`
Get all employees in a specific department.

**When to use**: When user asks about employees in a department

**Parameters**:
- `department` (string, required): Department name

**Example**: User asks "List all HR employees"

## How the LLM Calls Tools

The LLM uses a structured format to call tools:

### Format 1: JSON
```json
{
    "tool": "get_employee_by_id",
    "arguments": {
        "employee_id": "EMP001"
    }
}
```

### Format 2: Natural Language
```
CALL tool: get_employee_by_id with arguments: {"employee_id": "EMP001"}
```

### Format 3: Function Call
```
get_employee_by_id(employee_id="EMP001")
```

## Example Flow

### Example 1: Query with Employee ID

**User Query**: "What is the salary of EMP001?"

**Flow**:
1. RAG service retrieves relevant chunks from knowledge base
2. Multi-agent system receives query + context
3. LLM analyzes: "I need specific employee data, I should call get_employee_by_id"
4. LLM calls: `get_employee_by_id(employee_id="EMP001")`
5. Tool executes and returns employee data
6. LLM receives tool result
7. LLM generates final answer: "EMP001 (William Moore) has a salary of $1,455 USD"

### Example 2: Query without Employee ID

**User Query**: "Who works in the IT Support department?"

**Flow**:
1. RAG service retrieves relevant chunks
2. Multi-agent system receives query
3. LLM analyzes: "I need to search for employees by department"
4. LLM calls: `get_employees_by_department(department="IT Support")`
5. Tool returns list of employees
6. LLM generates answer with employee list

### Example 3: General Query (No Database Needed)

**User Query**: "What is RAG?"

**Flow**:
1. RAG service retrieves relevant chunks about RAG
2. Multi-agent system receives query + context
3. LLM analyzes: "This is a general question, I have enough context from knowledge base"
4. LLM generates answer directly from context (no tool call)

## API Usage

### Query Endpoint

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the salary of EMP001?",
    "max_chunks": 3
  }'
```

**Response**:
```json
{
  "answer": "EMP001 (William Moore) has a salary of $1,455 USD...",
  "relevant_chunks": [
    "Database Query Result - get_employee_by_id:\nEmployeeID: EMP001, Name: William Moore...",
    "..."
  ],
  "tool_calls_used": true
}
```

## Benefits of Multi-Agent System

1. **Intelligent Decision Making**: LLM decides when database access is needed
2. **Flexible Querying**: Handles both specific and general queries
3. **Automatic Tool Selection**: LLM chooses the right tool for the task
4. **Combined Context**: Uses both knowledge base and database information
5. **Natural Language**: Users can ask questions naturally without specifying tool names

## Configuration

### Enable/Disable Multi-Agent

In `rag_service.py`, the `query()` method accepts `use_multi_agent` parameter:

```python
# Use multi-agent (default)
answer, chunks = rag_service.query(query, use_multi_agent=True)

# Use traditional RAG (fallback)
answer, chunks = rag_service.query(query, use_multi_agent=False)
```

### Customize Tool Registry

Add new tools in `agent_tools.py`:

```python
def register_custom_tool(self):
    self.register_tool(
        name="my_custom_tool",
        description="Description of what the tool does",
        parameters={...},
        function=self._my_custom_function
    )
```

## Troubleshooting

### LLM Not Calling Tools

If the LLM doesn't call tools when it should:

1. **Check tool descriptions**: Ensure tools are clearly described
2. **Improve prompts**: The system prompt guides tool usage
3. **Model capability**: Some models are better at tool calling than others
4. **Query clarity**: Make sure queries clearly indicate database needs

### Tool Call Parsing Errors

The system uses multiple patterns to parse tool calls. If parsing fails:

1. Check LLM response format
2. Verify tool name matches registered tools
3. Ensure arguments are in correct format

### Database Connection Issues

If tools can't execute:

1. Verify database is running
2. Check database credentials in `db_utils.py`
3. Ensure `setup_database.py` was run successfully

## Advanced: Custom Tools

You can extend the system with custom tools:

```python
# In agent_tools.py
def _my_custom_tool(self, param1: str, param2: int) -> Dict:
    # Your custom logic
    result = do_something(param1, param2)
    return {"success": True, "data": result}

# Register it
self.register_tool(
    name="my_custom_tool",
    description="Does something useful",
    parameters={
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "integer"}
        },
        "required": ["param1", "param2"]
    },
    function=self._my_custom_tool
)
```

The LLM will automatically learn about and use your custom tools!

