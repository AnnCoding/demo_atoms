"""Regression tests for the v2 agent architecture (stdlib only)."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from core.events import event, normalize_questions
from core.intent import classify
from core.memory import ProjectMemory
from core.session import Session
from core.sse import bind_session, sse
from modes.registry import team_steps_after_triage
from main import app


class _MemoryStub:
    def __init__(self, *_): self.data = {"recent_messages": []}
    def load_snapshot(self): return self.data
    def remember_message(self, *_args, **_kwargs): return self.data
    def remember_fact(self, *_args, **_kwargs): return self.data
    def add_decision(self, *_): pass
    def append_progress(self, *_): pass
    def write_arch(self, *_): pass
    def write_code(self, *_): pass
    def save_meta(self, *_): pass


class ArchitectureV2Tests(unittest.TestCase):
    def test_questions_keep_machine_readable_choices(self):
        questions = normalize_questions([{
            "id": "format",
            "question": "交付形态？",
            "options": [
                {"id": "html", "label": "单页应用", "recommended": True},
                "多文件项目",
            ],
        }])
        self.assertEqual(questions[0]["type"], "single_select")
        self.assertEqual(questions[0]["options"][0]["id"], "html")
        self.assertTrue(questions[0]["options"][0]["recommended"])
        self.assertEqual(questions[0]["options"][1]["label"], "多文件项目")

    def test_event_envelope_is_versioned_and_sequenced(self):
        session = Session(id="s1", mode="team", idea="demo")
        first = event("phase", session=session, agent="Mike")
        second = event("done", session=session)
        self.assertEqual(first["schema_version"], "2.0")
        self.assertEqual((first["sequence"], second["sequence"]), (1, 2))
        self.assertEqual(first["session_id"], "s1")
        self.assertTrue(first["event_id"])

    def test_sse_uses_bound_session_context(self):
        session = Session(id="s2", mode="team", idea="demo")
        bind_session(session)
        payload = sse({"type": "phase", "agent": "Emma"})
        data = json.loads(payload.removeprefix("data: ").strip())
        self.assertEqual(data["session_id"], "s2")
        self.assertEqual(data["type"], "phase")

    def test_pre_intent_is_deterministic(self):
        result = classify("帮我重构一个带登录、数据库和后端 API 的 React 项目")
        self.assertEqual(result.task, "modify")
        self.assertEqual(result.output_format, "multi_file")
        self.assertEqual(result.complexity_hint, "complex")
        self.assertIn("bob", result.required_agents)

    def test_complex_pipeline_has_real_parallel_wave(self):
        steps = team_steps_after_triage("complex")
        discovery = [step for step in steps if step.parallel_group == "discovery"]
        self.assertEqual({step.agent for step in discovery}, {"emma", "iris"})
        self.assertTrue(next(step for step in discovery if step.agent == "emma").required)
        self.assertFalse(next(step for step in discovery if step.agent == "iris").required)

    def test_memory_is_durable_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("core.memory.PROJECTS_DIR", directory):
                memory = ProjectMemory("test")
                for index in range(20):
                    memory.remember_message("user", f"message-{index}")
                snapshot = memory.load_snapshot()
                self.assertEqual(len(snapshot["recent_messages"]), 16)
                self.assertEqual(snapshot["recent_messages"][-1]["content"], "message-19")

    def test_generate_api_stream_contract_without_listening_port(self):
        save = lambda session: {"id": session.project_id, "share_slug": "test"}
        with (
            patch.dict(os.environ, {"LLM_BASE_URL": "", "LLM_API_KEY": ""}),
            patch("core.orchestrator.ProjectMemory", _MemoryStub),
            patch("core.orchestrator.file_tools.set_workspace"),
            patch("core.orchestrator.file_tools.list_workspace_files", return_value=[]),
            patch("api.generate.save_project", save),
            patch("api.approve.save_project", save),
        ):
            response = TestClient(app).post("/api/generate", json={
                "mode": "team",
                "prompt": "做一个带登录、数据库和后端 API 的 React 项目",
            })
            self.assertEqual(response.status_code, 200)
            first_events = [
                json.loads(line.removeprefix("data: "))
                for line in response.text.splitlines() if line.startswith("data: ")
            ]
            confirmation = first_events[-1]
            self.assertEqual(confirmation["type"], "clarify")
            self.assertEqual(confirmation["purpose"], "requirement_confirmation")
            self.assertEqual(confirmation["questions"][0]["type"], "single_select")
            response = TestClient(app).post("/api/approve", json={
                "session_id": confirmation["session_id"],
                "answers": {
                    "output_format": "multi_file",
                    "scope_confirmation": "confirmed",
                },
            })
            events = [
                json.loads(line.removeprefix("data: "))
                for line in response.text.splitlines() if line.startswith("data: ")
            ]
        self.assertTrue(events)
        self.assertEqual(events[-1]["type"], "done")
        self.assertTrue(all(item["schema_version"] == "2.0" for item in events))
        self.assertIn("parallel_start", [item["type"] for item in events])


if __name__ == "__main__":
    unittest.main()
