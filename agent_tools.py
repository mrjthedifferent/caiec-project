"""
Tool/Function registry for multi-agent system
Defines available tools that the LLM can call
"""
from typing import Dict, List, Optional, Callable, Any
from db_utils import DatabaseManager
import json

class ToolRegistry:
    """Registry of available tools/functions for the LLM agent"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager
        self.tools: Dict[str, Dict] = {}
        self._register_tools()
    
    def _register_tools(self):
        """Register all available tools"""
        self.register_tool(
            name="get_employee_by_id",
            description="Get detailed information about an employee by their EmployeeID (e.g., EMP001, EMP002). Use this when the user asks about a specific employee ID.",
            parameters={
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "The employee ID (e.g., EMP001, EMP002)"
                    }
                },
                "required": ["employee_id"]
            },
            function=self._get_employee_by_id
        )
        
        self.register_tool(
            name="search_employees",
            description="Search for employees by name, email, department, or partial employee ID. Use this when the user asks about employees but doesn't provide a specific ID.",
            parameters={
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "Search term to find employees (name, email, department, or partial ID)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    }
                },
                "required": ["search_term"]
            },
            function=self._search_employees
        )
        
        self.register_tool(
            name="get_employees_by_department",
            description="Get all employees in a specific department. Use this when the user asks about employees in a department.",
            parameters={
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "description": "Department name (e.g., IT Support, HR, Finance)"
                    }
                },
                "required": ["department"]
            },
            function=self._get_employees_by_department
        )
    
    def register_tool(self, name: str, description: str, parameters: Dict, function: Callable):
        """Register a tool"""
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "function": function
        }
    
    def get_tools_description(self) -> str:
        """Get a formatted description of all tools for the LLM"""
        tools_desc = "Available Tools/Functions:\n\n"
        for tool_name, tool_info in self.tools.items():
            tools_desc += f"Tool: {tool_name}\n"
            tools_desc += f"Description: {tool_info['description']}\n"
            tools_desc += f"Parameters: {json.dumps(tool_info['parameters'], indent=2)}\n\n"
        return tools_desc
    
    def get_tools_json(self) -> List[Dict]:
        """Get tools in JSON format for LLM"""
        return [
            {
                "name": tool_info["name"],
                "description": tool_info["description"],
                "parameters": tool_info["parameters"]
            }
            for tool_info in self.tools.values()
        ]
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool with given arguments"""
        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' not found"}
        
        try:
            tool = self.tools[tool_name]
            result = tool["function"](**arguments)
            return result
        except Exception as e:
            return {"error": f"Error executing tool: {str(e)}"}
    
    # Tool implementations
    def _get_employee_by_id(self, employee_id: str) -> Dict:
        """Get employee by ID"""
        if not self.db_manager:
            return {"error": "Database not available"}
        
        employee = self.db_manager.get_employee_by_id(employee_id.upper())
        if employee:
            return {"success": True, "data": employee}
        else:
            return {"success": False, "error": f"Employee {employee_id} not found"}
    
    def _search_employees(self, search_term: str, limit: int = 10) -> Dict:
        """Search employees"""
        if not self.db_manager:
            return {"error": "Database not available"}
        
        employees = self.db_manager.search_employees(search_term, limit)
        return {"success": True, "data": employees, "count": len(employees)}
    
    def _get_employees_by_department(self, department: str) -> Dict:
        """Get employees by department"""
        if not self.db_manager:
            return {"error": "Database not available"}
        
        # Use search to find employees by department
        employees = self.db_manager.search_employees(department, limit=100)
        # Filter to exact department matches
        filtered = [emp for emp in employees if emp.get('Department', '').lower() == department.lower()]
        return {"success": True, "data": filtered, "count": len(filtered)}

