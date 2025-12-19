from pathlib import Path
from agents import Agent, Runner, function_tool, HostedMCPTool
from agents.mcp import MCPServerStdio
from agents.model_settings import ModelSettings
from agents.mcp import MCPServerStreamableHttp
from dotenv import load_dotenv
import asyncio

from openai.types.responses import ResponseTextDeltaEvent



load_dotenv()

# async def main():
    
    # async with MCPServerStdio(name = "odoo mcp server",
    #                             params = {
    #                                 "command" : "C:\\Users\\TempAccess\\Documents\\Dhruv\\Odoo\\Odoo_github_Dhruv_Panchal\\.venv\\Scripts\\python.exe",
    #                                 "args" : ["C:\\Users\\TempAccess\\Documents\\Dhruv\\Odoo\\Odoo_github_Dhruv_Panchal\\run_server.py"]
    #                             }) as server:
    
    #     agent = Agent(
    #         name= "Assistant",
    #         instructions= "To answer Odoo related query",
    #         mcp_servers= [server],
    #         model= "gpt-5",
    #         model_settings=ModelSettings(tool_choice="required")
    #     )
        
    #     result = await Runner.run(agent, "Retrieve the top customers based on their total sales ? all the other things deside on yourself")
        
    #     print(result.final_output)

async def main():

    async with MCPServerStreamableHttp(name = "http odoo mcp server",
                                params = {
                                    "url" : "http://localhost:8000/mcp",
                                    "timeout" : 10
                                }
        ) as server:

        agent = Agent(
            name= "Assistant",
            instructions= "To answer Odoo related query",
            mcp_servers= [server],
            model_settings=ModelSettings(tool_choice="required"),
            
        )
        
        # result = await Runner.run(agent, "find the top 5 by invoiced amount or sales order amount? count all and all things diside by your self only")
        result = Runner.run_streamed(agent, input="find the top 5 by invoiced amount or sales order amount? count all and all things diside by your self only.")
        
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                print(event.data.delta, end="", flush=True)

        # print(result.final_output)
    
        
if __name__ == "__main__":
    asyncio.run(main())