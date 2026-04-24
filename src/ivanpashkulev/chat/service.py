from typing import AsyncIterator
import os
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.document_loaders import PyMuPDFLoader
from langgraph.graph import StateGraph, MessagesState, START, END
from ivanpashkulev.core.config import settings


class ChatService:

    def __init__(self, model: str = "deepseek-r1:8b"):
        self.llm = ChatOllama(base_url=settings.ollama_base_url, model=model)
        self._context = self._load_documents()
        self._graph = self._build_graph()

    def _load_documents(self) -> str:
        context = ""
        for filename in os.listdir(settings.assets_path):
            filepath = os.path.join(settings.assets_path, filename)
            if filename.endswith(".pdf"):
                loader = PyMuPDFLoader(filepath)
                docs = loader.load()
                context += "\n\n".join(doc.page_content for doc in docs)
            elif filename.endswith((".txt", ".md")):
                with open(filepath, "r", encoding="utf-8") as f:
                    context += f.read()
        return context

    def _system_prompt(self) -> str:
        return (
            "You are acting as Ivan Pashkulev. You are answering questions on Ivan's website, "
            "particularly questions related to Ivan's career, background, skills and experience. "
            "Your responsibility is to represent Ivan as faithfully as possible. "
            "Be professional and engaging, as if talking to a potential client or future employer.\n\n"
            f"## Context:\n{self._context}\n\n"
            "With this context, please chat with the user, always staying in character as Ivan Pashkulev."
        )

    def _build_graph(self):
        def llm_call(state: MessagesState):
            messages = [SystemMessage(content=self._system_prompt())] + state["messages"]
            return {"messages": [self.llm.invoke(messages)]}

        graph = StateGraph(MessagesState)
        graph.add_node("llm_call", llm_call)
        graph.add_edge(START, "llm_call")
        graph.add_edge("llm_call", END)
        return graph.compile()

    def _build_messages(self, message: str, history: list[dict]) -> list:
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=message))
        return messages

    async def stream(self, message: str, history: list[dict]) -> AsyncIterator[str]:
        async for event in self._graph.astream_events(
            {"messages": self._build_messages(message, history)}, version="v2"
        ):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"].content
                if chunk:
                    yield chunk
