"""
Multi-Agent System with ReAct-style tool calling
The LLM agent can decide when to call database tools
"""
import requests
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from agent_tools import ToolRegistry
from db_utils import DatabaseManager

class MultiAgentSystem:
    """Multi-agent system where LLM can call tools/functions"""
    
    def __init__(self, ollama_base_url: str, model_name: str, db_manager: Optional[DatabaseManager] = None):
        self.ollama_base_url = ollama_base_url
        self.model_name = model_name
        self.tool_registry = ToolRegistry(db_manager)
        self.max_iterations = 5  # Maximum tool calling iterations
    
    def _format_tool_result(self, tool_name: str, result: Any) -> str:
        """Format tool result for LLM context"""
        if isinstance(result, dict):
            if result.get("error"):
                return f"Tool '{tool_name}' returned an error: {result['error']}"
            elif result.get("success"):
                data = result.get("data", [])
                if isinstance(data, list):
                    if len(data) == 0:
                        return f"Tool '{tool_name}' found no results."
                    elif len(data) == 1:
                        return f"Tool '{tool_name}' result:\n{json.dumps(data[0], indent=2, default=str)}"
                    else:
                        return f"Tool '{tool_name}' found {len(data)} results:\n{json.dumps(data, indent=2, default=str)}"
                else:
                    return f"Tool '{tool_name}' result:\n{json.dumps(data, indent=2, default=str)}"
            else:
                return f"Tool '{tool_name}' result:\n{json.dumps(result, indent=2, default=str)}"
        else:
            return f"Tool '{tool_name}' result: {str(result)}"
    
    def _extract_tool_call(self, response: str) -> Optional[Dict]:
        """Extract tool call from LLM response using structured format"""
        # Pattern 1: JSON format
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        # Pattern 2: Simple JSON object
        json_pattern2 = r'\{[^{}]*"tool"[^{}]*\}'
        match = re.search(json_pattern2, response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        # Pattern 3: Function call format
        func_pattern = r'(?:CALL|call|use|USE)\s+(?:tool|function|Tool|Function)[:\s]+(\w+)\s*(?:with|WITH)?\s*(?:arguments|args|params)?[:\s]*(\{.*?\})?'
        match = re.search(func_pattern, response, re.IGNORECASE | re.DOTALL)
        if match:
            tool_name = match.group(1)
            args_str = match.group(2) if match.group(2) else "{}"
            try:
                args = json.loads(args_str) if args_str.strip() else {}
                return {"tool": tool_name, "arguments": args}
            except:
                return {"tool": tool_name, "arguments": {}}
        
        # Pattern 4: Simple format: TOOL_NAME(arg1="value1", arg2="value2")
        simple_pattern = r'(\w+)\s*\(([^)]*)\)'
        match = re.search(simple_pattern, response)
        if match:
            tool_name = match.group(1)
            if tool_name in self.tool_registry.tools:
                args_str = match.group(2)
                args = {}
                # Simple parsing of key="value" pairs
                for arg_match in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', args_str):
                    args[arg_match.group(1)] = arg_match.group(2)
                if args:
                    return {"tool": tool_name, "arguments": args}
        
        return None
    
    def _call_ollama(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call Ollama API"""
        try:
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500
                    }
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            raise Exception(f"Error calling Ollama: {str(e)}")
    
    def query(self, user_query: str, context: Optional[str] = None) -> Tuple[str, List[Dict]]:
        """
        Process query using multi-agent system with tool calling
        Returns: (final_answer, tool_calls_history)
        """
        tools_description = self.tool_registry.get_tools_description()
        tool_calls_history = []
        
        # Initial system prompt
        system_prompt = f"""You are an intelligent assistant with access to database tools. 
When you need to query the employee database, you can call tools.

{tools_description}

To call a tool, respond in JSON format:
{{
    "tool": "tool_name",
    "arguments": {{"param1": "value1", "param2": "value2"}}
}}

Or use this format:
CALL tool: tool_name with arguments: {{"param1": "value1"}}

After calling a tool, you will receive the results. Use those results to answer the user's question.
If you don't need to call a tool, just answer the question directly."""
        
        conversation_history = []
        if context:
            conversation_history.append(f"Context from knowledge base:\n{context}\n")
        
        conversation_history.append(f"User Question: {user_query}\n")
        
        current_query = "\n".join(conversation_history)
        current_query += "\n\nThink step by step. Do you need to call a tool to answer this question? If yes, call the appropriate tool. If no, answer directly."
        
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            
            # Get LLM response
            response = self._call_ollama(current_query, system_prompt)
            conversation_history.append(f"Assistant: {response}\n")
            
            # Check if LLM wants to call a tool
            tool_call = self._extract_tool_call(response)
            
            if tool_call and "tool" in tool_call:
                tool_name = tool_call["tool"]
                arguments = tool_call.get("arguments", {})
                
                # Execute tool
                tool_result = self.tool_registry.call_tool(tool_name, arguments)
                formatted_result = self._format_tool_result(tool_name, tool_result)
                
                tool_calls_history.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": tool_result
                })
                
                # Add tool result to conversation
                conversation_history.append(f"Tool '{tool_name}' was called with arguments {arguments}.\nResult: {formatted_result}\n")
                
                # Continue conversation with tool result
                current_query = "\n".join(conversation_history)
                current_query += "\n\nBased on the tool result above, provide a final answer to the user's question. If you need more information, you can call another tool. Otherwise, provide a complete answer."
            else:
                # No tool call, LLM provided direct answer
                final_answer = response
                # Clean up the answer (remove tool call artifacts if any)
                final_answer = re.sub(r'```json.*?```', '', final_answer, flags=re.DOTALL)
                final_answer = re.sub(r'CALL\s+tool.*', '', final_answer, flags=re.IGNORECASE | re.DOTALL)
                final_answer = final_answer.strip()
                
                return final_answer, tool_calls_history
        
        # Max iterations reached
        final_answer = conversation_history[-1] if conversation_history else "I apologize, but I'm having trouble processing your request."
        return final_answer, tool_calls_history

