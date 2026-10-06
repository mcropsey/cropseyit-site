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
                args = json.loads(call.function.arguments or "{}")
                result = await mcp.call_tool(call.function.name, args)
                text = "\n".join(c.text for c in result.content if c.type == "text")
                print(f"  [mcp] {call.function.name}({args}) -> {text}", file=sys.stderr)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": text})


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "What IP does rocky-linux resolve to, and is port 4000 open on 192.168.1.101?"))
