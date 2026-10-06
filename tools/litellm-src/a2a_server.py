"""Serve the agent from agent.py over A2A (Agent2Agent), so other agents can call it."""
import asyncio
import os

import uvicorn
from a2a.helpers import get_message_text, new_task_from_user_message, new_text_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill, TaskState
from starlette.applications import Starlette

import agent  # the Lab 5 agent: agent.run(question) -> answer

NAME = os.environ.get("AGENT_NAME", "ops-agent")
DESCRIPTION = os.environ.get("AGENT_DESCRIPTION", "Checks home-lab hosts, ports and URLs.")
PORT = int(os.environ.get("PORT", "8601"))
PUBLIC_URL = os.environ["PUBLIC_URL"]  # how other hosts reach this agent, e.g. http://192.168.1.100:8601


class Executor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task or new_task_from_user_message(context.message)
        if not context.current_task:
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)
        await updater.update_status(state=TaskState.TASK_STATE_WORKING, message=new_text_message("Working..."))

        answer = await asyncio.to_thread(agent.run, get_message_text(context.message) or "")

        await updater.add_artifact(parts=[new_text_part(text=answer, media_type="text/plain")])
        await updater.update_status(state=TaskState.TASK_STATE_COMPLETED, message=new_text_message(answer))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError


card = AgentCard(
    name=NAME,
    description=DESCRIPTION,
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=False),
    supported_interfaces=[AgentInterface(protocol_binding="JSONRPC", url=PUBLIC_URL, protocol_version="1.0")],
    skills=[AgentSkill(id=NAME, name=NAME, description=DESCRIPTION, tags=["lab"])],
)
handler = DefaultRequestHandler(agent_executor=Executor(), task_store=InMemoryTaskStore(), agent_card=card)
app = Starlette(routes=[*create_agent_card_routes(card), *create_jsonrpc_routes(handler, "/")])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
