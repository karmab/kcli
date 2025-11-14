import ast
from a2a.types import AgentCard, AgentSkill
from google.adk.agents.llm_agent import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from shutil import which
import os
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

DESCRIPTION = 'Manages VMs and Kubernetes clusters using kcli'
INSTRUCTION = """You are a helpful assistant that can manage virtual machines and kubernetes cluster on
any virtualization and cloud provider using the provided tools for this purpose."""
MCP_PATH = which('kmcp')

MODEL = os.getenv('MODEL', 'gemini-2.5-flash')
IP = os.getenv('IP', '127.0.0.1')
PORT = os.getenv('PORT', 8001)
if os.getenv('GOOGLE_API_KEY') is None:
    print("Missing GOOGLE_API_KEY env variable")
    os._exit(1)


def get_skills():
    skills = []
    for node in ast.walk(ast.parse(open(MCP_PATH, "r").read())):
        if isinstance(node, ast.FunctionDef):
            name = node.name
            docstring = ast.get_docstring(node)
            if docstring is not None:
                skills.append(AgentSkill(id=name, name=name, description=docstring, tags=['kcli']))
    return skills


tools = McpToolset(connection_params=StdioConnectionParams(
    server_params=StdioServerParameters(command='python3', args=[MCP_PATH]), timeout=120), tool_filter=[])
agent_card = AgentCard(name="kcli_agent",
                       url=f"http://{IP}:{PORT}",
                       description="Agent that manages VMs and Kubernetes clusters using kcli",
                       version="1.0.0",
                       capabilities={},
                       skills=get_skills(),
                       defaultInputModes=["text/plain"],
                       defaultOutputModes=["text/plain"],
                       supportsAuthenticatedExtendedCard=False
                       )
root_agent = Agent(model=MODEL, name='kcli_agent', description=DESCRIPTION, instruction=INSTRUCTION,
                   tools=[tools])
a2a_app = to_a2a(root_agent, port=PORT, agent_card=agent_card)


def main():
    print(f"Agent card is available at http://{IP}:{PORT}/.well-known/agent-card.json")
    import uvicorn
    uvicorn.run(a2a_app, host="0.0.0.0", port=PORT)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        os._exit(0)
