"""chat.py: a terminal chat client. Every message goes through the LiteLLM gateway."""
import os

from openai import OpenAI

client = OpenAI(base_url=os.environ["GW"] + "/v1", api_key=os.environ["KEY"])
MODEL = os.environ.get("MODEL", "lab-chat")

# The API has no memory. The conversation lives in this list, and the
# whole list is sent with every request.
history = [{"role": "system", "content": "You are a helpful assistant. Keep answers short."}]

print(f"Chatting with {MODEL} through {os.environ['GW']}. Ctrl-D to quit.")
while True:
    try:
        question = input("\nyou> ").strip()
    except EOFError:
        break
    if not question:
        continue
    history.append({"role": "user", "content": question})

    stream = client.chat.completions.create(model=MODEL, messages=history, stream=True)
    print("ai > ", end="", flush=True)
    answer = ""
    for chunk in stream:                       # print each piece as it arrives
        piece = chunk.choices[0].delta.content if chunk.choices else None
        if not piece:
            continue
        answer += piece
        print(piece, end="", flush=True)
    print()
    history.append({"role": "assistant", "content": answer})
