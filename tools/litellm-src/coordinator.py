"""coordinator: an agent whose only tool is "ask another agent" through the gateway."""
import json
import os
import sys
import uuid

import httpx
from openai import OpenAI

GW, KEY = os.environ["GW"], os.environ["AGENT_KEY"]
llm = OpenAI(base_url=GW + "/v1", api_key=KEY)
auth = {"Authorization": f"Bearer {KEY}"}


def list_agents() -> dict:
    """Ask the gateway which agents this key can see: {name: description}."""
    r = httpx.get(f"{GW}/v1/agents", headers=auth, timeout=30)
    r.raise_for_status()
    return {a["agent_name"]: a["agent_card_params"].get("description", "") for a in r.json()}


def ask_agent(agent: str, message: str) -> str:
    """Send one A2A message to an agent through the gateway and return its reply text."""
    body = {"jsonrpc": "2.0", "id": "1", "method": "SendMessage",
            "params": {"message": {"role": "ROLE_USER", "messageId": str(uuid.uuid4()),
                                   "parts": [{"text": message}]}}}
    r = httpx.post(f"{GW}/a2a/{agent}", json=body, headers={**auth, "A2A-Version": "1.0"}, timeout=300)
    data = r.json()
    if "error" in data:
        return f"error from {agent}: {data['error']}"
    task = data["result"]["task"]
    return "\n".join(p.get("text", "") for p in task["status"]["message"]["parts"])


def main(goal: str) -> None:
    agents = list_agents()
    print("agents on the gateway:", list(agents), file=sys.stderr)
    if not agents:
        sys.exit("This key isn't allowed to use any agents.")
    roster = "\n".join(f"- {name}: {desc}" for name, desc in agents.items())
    tools = [{"type": "function", "function": {
        "name": "ask_agent", "description": "Delegate a task to one of the available agents.",
        "parameters": {"type": "object", "required": ["agent", "message"], "properties": {
            "agent": {"type": "string", "enum": list(agents)},
            "message": {"type": "string", "description": "A complete, self-contained request."}}}}}]
    messages = [
        {"role": "system", "content": "You are a coordinator. You cannot check anything yourself. "
                                      "Break the goal into steps and delegate each step to the best agent:\n" + roster},
        {"role": "user", "content": goal}]
    for _ in range(8):
        msg = llm.chat.completions.create(model="lab-agent", messages=messages, tools=tools).choices[0].message
        if not msg.tool_calls:
            print(msg.content)
            return
        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            print(f"  -> {args['agent']}: {args['message']}", file=sys.stderr)
            answer = ask_agent(**args)
            print(f"  <- {args['agent']}: {answer[:200]}", file=sys.stderr)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": answer})


if __name__ == "__main__":
    main(" ".join(sys.argv[1:]) or "Check whether the gateway (http://192.168.1.101:4000/health/liveliness) "
                                    "and SSH on 192.168.1.100 are up, then have the results written up as a status update.")
