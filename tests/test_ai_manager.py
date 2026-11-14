# tests for OOP/ai_manager.py
# the OpenAI client is swapped for a mock, so nothing is ever sent to the real API

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import openai

from OOP.ai_manager import AIManager


JOB = {"title": "Backend Dev", "required_skills": ["Python"], "preferred": ["SQL"],
       "min_experience": 2, "education": "Degree"}


def valid_ai_payload():
    return {
        "skills": [
            {"name": "Python", "category": "must_have", "present": True,
             "last_used_year": 2026, "evidence": "Built Python tools"},
        ],
        "experience_score": 80,
        "education_score": 70,
        "overall_score": 75,
        "confidence": "high",
        "summary": "Good fit",
    }


def fake_response(content):
    # mimic the shape of an OpenAI chat completion response
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


# stop load_dotenv from reading a real .env file and use a dummy key instead
@patch("OOP.ai_manager.load_dotenv", lambda: None)
@patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=True)
class TestAIManager(unittest.TestCase):

    def make_manager(self):
        manager = AIManager()
        manager.client = MagicMock()
        return manager

    def test_missing_api_key_raises_value_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                AIManager()

    def test_prompt_includes_job_details_and_resume(self):
        prompt = self.make_manager()._build_user_prompt(JOB, "Resume text here")
        self.assertIn("Backend Dev", prompt)
        self.assertIn("Python", prompt)
        self.assertIn("SQL", prompt)
        self.assertIn("Resume text here", prompt)

    def test_process_resume_returns_validated_data(self):
        manager = self.make_manager()
        manager.client.chat.completions.create.return_value = fake_response(
            json.dumps(valid_ai_payload())
        )
        result = manager.process_resume(JOB, "Some resume")
        self.assertEqual(result["experience_score"], 80)
        manager.client.chat.completions.create.assert_called_once()

    def test_non_json_reply_is_rejected(self):
        manager = self.make_manager()
        with self.assertRaises(ValueError):
            manager._parse_response(fake_response("this is not json"))

    def test_empty_reply_is_rejected(self):
        manager = self.make_manager()
        with self.assertRaises(ValueError):
            manager._parse_response(fake_response(""))
        with self.assertRaises(ValueError):
            manager._parse_response(SimpleNamespace(choices=[]))

    def test_schema_validation_catches_bad_fields(self):
        manager = self.make_manager()
        broken_payloads = []

        missing_field = valid_ai_payload()
        del missing_field["confidence"]
        broken_payloads.append(missing_field)

        out_of_range = valid_ai_payload()
        out_of_range["experience_score"] = 150
        broken_payloads.append(out_of_range)

        bad_confidence = valid_ai_payload()
        bad_confidence["confidence"] = "very sure"
        broken_payloads.append(bad_confidence)

        bad_category = valid_ai_payload()
        bad_category["skills"][0]["category"] = "nice_to_have"
        broken_payloads.append(bad_category)

        bool_score = valid_ai_payload()
        bool_score["overall_score"] = True
        broken_payloads.append(bool_score)

        for payload in broken_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    manager._validate_ai_result(payload)

    def test_non_retryable_api_error_becomes_value_error(self):
        manager = self.make_manager()
        manager.client.chat.completions.create.side_effect = openai.OpenAIError("boom")
        with self.assertRaises(ValueError):
            manager.process_resume(JOB, "Some resume")

    def test_retryable_api_error_becomes_connection_error(self):
        manager = self.make_manager()
        manager.client.chat.completions.create.side_effect = openai.OpenAIError("slow")
        # pretend the SDK classified this as a temporary problem
        with patch.object(manager, "_can_retry_error", return_value=True):
            with self.assertRaises(ConnectionError):
                manager.process_resume(JOB, "Some resume")


if __name__ == "__main__":
    unittest.main()
