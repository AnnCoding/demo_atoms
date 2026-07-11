"""Agent 注册表:7 个智能体。"""
from dataclasses import dataclass


@dataclass
class AgentDef:
    id: str
    name: str
    role: str
    emoji: str
    prompt_key: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "role": self.role,
                "emoji": self.emoji, "prompt_key": self.prompt_key}


AGENTS = {
    "mike":  AgentDef("mike",  "Mike",  "Team Leader",       "🧑‍💼", "mike"),
    "emma":  AgentDef("emma",  "Emma",  "Product Manager",   "📋", "emma"),
    "bob":   AgentDef("bob",   "Bob",   "System Architect",  "🏗", "bob"),
    "alex":  AgentDef("alex",  "Alex",  "Software Engineer", "⚙️", "alex"),
    "david": AgentDef("david", "David", "Data Scientist",    "📊", "david"),
    "iris":  AgentDef("iris",  "Iris",  "Deep Researcher",   "🔬", "iris"),
    "sarah": AgentDef("sarah", "Sarah", "SEO Specialist",    "📈", "sarah"),
}


def list_agents() -> list:
    return [a.to_dict() for a in AGENTS.values()]
