"""附件暂存(内存)。"""
from typing import Dict

from .models import Attachment

ATTACHMENTS: Dict[str, Attachment] = {}


def put(a: Attachment):
    ATTACHMENTS[a.id] = a


def get(aid: str):
    return ATTACHMENTS.get(aid)
