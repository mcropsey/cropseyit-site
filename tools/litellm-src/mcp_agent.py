"""mcp-agent: an agent that gets its tools from the gateway's MCP endpoint.

The agent has no tools of its own. It asks LiteLLM which MCP tools its key may
use, hands them to the model, and runs the model's tool calls through LiteLLM.
"""
import asyncio
import json
import os
import sys

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from openai import OpenAI

GW, KEY = os.environ["GW"], os.environ["AGENT_KEY"]
llm = OpenAI(base_url=GW + "/v1", api_key=KEY)
SYSTEM = "You are a home-lab operations assistant. Use the tools to check facts. Answer briefly."


async def call_tool(mcp: Client, name: str, arguments: str) -> str:
    """Run one tool through the gateway. Mistakes go back to the model as text, so it can retry."""
    try:
        result = await mcp.call_tool(name, json.loads(arguments or "{}"))
    except Exception as err:                    # bad JSON from the model, or the gateway refused the call
        return f"error: {err}"
    return "\n".join(c.text for c in result.content if c.type == "text")


async def main(question: str) -> None:
    http = httpx2.AsyncClient(headers={"Authorization": f"Bearer {KEY}"}, timeout=60)
    async with Client(streamable_http_client(GW + "/mcp/", http_client=http)) as mcp:
        tools = (await mcp.list_tools()).tools
        print("tools from the gateway:", [t.name for t in tools], file=sys.stderr)
        specs = [{"type": "function", "function": {
            "name": t.name, "description": t.description or "", "parameters": t.input_schema}} for t in tools]

        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
        for _ in range(8):
            msg = llm.chat.completions.create(model="lab-agent", messages=messages, tools=specs).choices[0].message
            if not msg.tool_calls:
                print(msg.content)
                return
            messages.append(msg.model_dump(exclude_none=True))
            for call in msg.tool_calls:
                text = await call_tool(mcp, call.function.name, call.function.arguments)
                print(f"  [mcp] {call.function.name}({call.function.arguments}) -> {text}", file=sys.stderr)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": text})
        print("Stopped: too many steps.")


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "What IP does rocky-linux resolve to, and is port 4000 open on 192.168.1.101?"))
