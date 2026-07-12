"""Tests for user-installable skills and private/public knowledge flows."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from agents.skills.base import SkillManager
from context.models import Attachment
from knowledge import store as knowledge_store
from skills import store as skill_store


VALID_SKILL = b"""name: ux-audit
display_name: UX Audit
description: Review interaction quality
category: design
trigger_keywords: [ux audit]
target_agent: alex
collaborator_agents: [mike]
required_tools: []
default_router: false
instructions: |
  Review every interaction state and return a prioritized usability checklist.
"""


class ExtensibilityTests(unittest.TestCase):
    def test_skill_install_pipeline_and_runtime_toggle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "_registry.json"
            with (
                patch.object(skill_store, "USER_SKILLS_DIR", root),
                patch.object(skill_store, "REGISTRY_PATH", registry),
            ):
                result = skill_store.SkillInstallPipeline().install(VALID_SKILL, "ux-audit.yaml")
                self.assertEqual(
                    [stage["name"] for stage in result["pipeline"]],
                    ["parse", "validate", "persist", "activate"],
                )
                manager = SkillManager()
                manager.load_custom_skills(root)
                self.assertIsNotNone(manager.get("ux-audit"))
                skill_store.set_enabled("ux-audit", False)
                disabled_manager = SkillManager()
                disabled_manager.load_custom_skills(root)
                self.assertIsNone(disabled_manager.get("ux-audit"))

    def test_skill_rejects_unknown_executable_tool(self):
        invalid = VALID_SKILL.replace(b"required_tools: []", b"required_tools: [shell_exec]")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch.object(skill_store, "USER_SKILLS_DIR", root),
                patch.object(skill_store, "REGISTRY_PATH", root / "_registry.json"),
            ):
                with self.assertRaisesRegex(ValueError, "未知工具"):
                    skill_store.SkillInstallPipeline().install(invalid, "unsafe.yaml")

    def test_knowledge_private_memory_and_explicit_publish(self):
        attachment = Attachment(
            id="attachment", filename="guide.txt", mime="text/plain", kind="text",
            text="private product handbook", storage_url="local://guide.txt",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = root / "memory"
            memory.mkdir()
            with (
                patch.object(knowledge_store, "DATA_DIR", root),
                patch.object(knowledge_store, "ITEMS_PATH", root / "items.json"),
                patch.object(knowledge_store, "MEMORY_DIR", memory),
                patch.object(knowledge_store, "ingest", AsyncMock(return_value=attachment)),
            ):
                item = asyncio.run(knowledge_store.create(
                    b"private product handbook", "guide.txt", "text/plain",
                    title="Product Handbook", tags="product,internal", owner_id="alice",
                ))
                self.assertEqual(knowledge_store.list_square(), [])
                self.assertEqual(knowledge_store.memory_context("alice")[0]["title"], "Product Handbook")
                knowledge_store.update(item["id"], {"published": True}, "alice")
                self.assertEqual(knowledge_store.list_square()[0]["id"], item["id"])
                public_attachment = knowledge_store.as_attachment(item["id"], "bob")
                self.assertIn("handbook", public_attachment.text)


if __name__ == "__main__":
    unittest.main()
