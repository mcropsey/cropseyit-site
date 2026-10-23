"""search-agent: answers from fresh web results. Searches and model calls both go through the gateway."""
import json
import os
import sys

import httpx
from openai import OpenAI

GW, KEY = os.environ["GW"], os.environ["AGENT_KEY"]
client = OpenAI(base_url=GW + "/v1", api_key=KEY)
MODEL = os.environ.get("AGENT_MODEL", "qwen3.8-27b")


def web_search(query: str) -> str:
    """Ask the gateway's web-search tool and return the top five results as text."""
    r = httpx.post(f"{GW}/v1/search/web-search", headers={"Authorization": f"Bearer {KEY}"},
                   json={"query": query}, timeout=30)
    if r.status_code != 200:
        return f"search failed: HTTP {r.status_code} {r.text[:200]}"
    results = r.json().get("results", [])[:5]
    return "\n\n".join(f"{x['title']}\n{x['url']}\n{x.get('snippet', '')}" for x in results) or "no results"


TOOL_SPECS = [{"type": "function", "function": {
    "name": "web_search", "description": "Search the web. Returns titles, URLs and snippets.",
    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}}]
SYSTEM = ("You are search-agent. For anything that may have changed recently, search first, "
          "then answer briefly and list the URLs you used.")


def run(question: str, max_steps: int = 6) -> str:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    for _ in range(max_steps):
        msg = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOL_SPECS).choices[0].message
        if not msg.tool_calls:                      # no search requested: this is the answer
            return msg.content
        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:
            query = json.loads(call.function.arguments or "{}").get("query", "")
            print(f"  [search] {query}", file=sys.stderr)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": web_search(query)})
    return "Stopped: too many steps."


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "What is the newest Rocky Linux release, and when did it come out?"))
