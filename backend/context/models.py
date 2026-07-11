"""统一多模态 Context。"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Attachment:
    id: str
    filename: str
    mime: str
    kind: str               # text | image | code | pdf
    text: Optional[str] = None
    image_url: Optional[str] = None
    storage_url: str = ""


@dataclass
class Context:
    idea: str
    attachments: List[Attachment] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)

    def attachments_text(self) -> str:
        """文本类附件拼进 prompt;图片走多模态(在 llm 处理)。"""
        return "\n\n".join(f"## {a.filename}\n{a.text}"
                           for a in self.attachments if a.text)
