"""ops-agent: a small tool-using agent. Every model call goes through the LiteLLM gateway."""
import json
import os
import socket
import sys
import time
from datetime import datetime, timezone

import httpx
from openai import OpenAI

client = OpenAI(base_url=os.environ["GW"] + "/v1", api_key=os.environ["AGENT_KEY"])
MODEL = os.environ.get("AGENT_MODEL", "lab-agent")


# ---- the tools: plain Python functions -------------------------------------
def get_time() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def check_url(url: str) -> str:
    start = time.monotonic()
    try:
        r = httpx.get(url, timeout=5, follow_redirects=True)
        return f"HTTP {r.status_code} in {(time.monotonic() - start) * 1000:.0f} ms"
    except httpx.HTTPError as err:
        return f"failed: {err!r}"


def check_port(host: str, port: int) -> str:
    try:
        with socket.create_connection((host, int(port)), timeout=3):
            return f"{host}:{port} is open"
    except OSError as err:
        return f"{host}:{port} is closed or unreachable ({err})"


TOOLS = {"get_time": get_time, "check_url": check_url, "check_port": check_port}


def call_tool(name: str, arguments: str) -> str:
    """Run one tool the model asked for. Mistakes go back to the model as text, so it can retry."""
    if name not in TOOLS:
        return f"error: there is no tool called {name!r}"
    try:
        return TOOLS[name](**json.loads(arguments or "{}"))
    except (json.JSONDecodeError, TypeError) as err:
        return f"error: bad arguments for {name}: {err}"


# ---- how the model learns about the tools: JSON Schema descriptions --------
TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "get_time", "description": "Current date and time in UTC.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "check_url", "description": "Fetch a URL and report the HTTP status and response time.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "check_port", "description": "Test whether a TCP port on a host accepts connections.",
        "parameters": {"type": "object", "properties": {"host": {"type": "string"}, "port": {"type": "integer"}},
                       "required": ["host", "port"]}}},
]

# A2A services (Lab 6) reuse this file and override these two settings per agent.
SYSTEM = os.environ.get("AGENT_PROMPT", "You are ops-agent, a home-lab operations assistant. "
                        "Use the tools to check facts instead of guessing. Answer briefly.")
USE_TOOLS = os.environ.get("AGENT_TOOLS", "on") == "on"


# ---- the agent loop ---------------------------------------------------------
def run(question: str, max_steps: int = 8) -> str:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    for _ in range(max_steps):
        extra = {"tools": TOOL_SPECS} if USE_TOOLS else {}
        reply = client.chat.completions.create(model=MODEL, messages=messages, **extra)
        msg = reply.choices[0].message
        if not msg.tool_calls:                      # no tool requested: this is the answer
            return msg.content
        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:                 # run each requested tool, return the result
            result = call_tool(call.function.name, call.function.arguments)
            print(f"  [tool] {call.function.name}({call.function.arguments}) -> {result}", file=sys.stderr)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return "Stopped: too many steps."


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "Is the gateway at 192.168.1.101 port 4000 up, and what time is it?"))
