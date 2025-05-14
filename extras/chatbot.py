import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

import sys

model = ChatOpenAI(model='granite3.2:latest', base_url='http://127.0.0.1:4000/v1', api_key='xxx')

server_params = StdioServerParameters(command="kmcp.py")


async def main_chat():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_react_agent(model, tools)

            print("Terminal chatbot is ready. Type 'exit' to quit.")
            chat_history = []

            while True:
                user_input = input("You: ").strip()
                if user_input.lower() in {"exit", "quit"}:
                    print("Exiting chatbot.")
                    break

                chat_history.append({"role": "user", "content": user_input})

                while True:
                    result = await agent.ainvoke({"messages": chat_history})
                    last_message = result["messages"][-1]

                    # Check if it's a tool_use message
                    if hasattr(last_message, 'type') and last_message.type == "tool_use":
                        # Agent wants to call a tool → MCP server handles it automatically
                        tool_name = last_message.tool_call[0]['name']
                        tool_args = last_message.tool_call[0]['args']
                        print(f"[Agent is calling tool '{tool_name}' with args {tool_args}]")

                        # Append tool_use message to chat history so agent remembers it
                        chat_history.append({"role": "user", "content": f"Calling tool: {tool_name}"})
                        continue  # Run agent again to get tool result processed

                    # Otherwise — final bot response
                    bot_reply = last_message.content
                    print(f"Bot: {bot_reply}")
                    chat_history.append({"role": "assistant", "content": bot_reply})
                    break


if __name__ == "__main__":
    try:
        asyncio.run(main_chat())
    except KeyboardInterrupt:
        print("\nChatbot interrupted. Exiting.")
        sys.exit(0)
