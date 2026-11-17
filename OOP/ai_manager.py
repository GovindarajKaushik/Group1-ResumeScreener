import json
import math
import os
import openai
from dotenv import load_dotenv
from openai import OpenAI


# OpenRouter API gateway: builds prompts, calls the API, and validates JSON output
class AIManager:

    # prompt to AI
    SYSTEM_PROMPT = """You are an expert recruiter assisting with resume screening.
Compare the candidate resume with the job requirements using semantic understanding: treat equivalent skills described with different wording as a match (e.g. "built REST services" satisfies "API development").
Base every judgement ONLY on the resume text. Never consider or infer personal attributes such as name, age, gender, ethnicity or marital status.
Respond with ONE JSON object and nothing else (no markdown, no commentary), using exactly this schema:
{
  "skills": [
    {"name": "<skill from the job requirements>",
     "category": "must_have" or "preferred",
     "present": true or false,
     "last_used_year": <integer year the skill was last used, or null if unknown/absent>,
     "evidence": "<short exact excerpt from the supplied resume supporting this skill, or empty if unavailable>"}
  ],
  "experience_score": <0-100, how well the candidate's experience matches the role>,
  "experience_summary": "<1-2 sentences>",
  "education_score": <0-100, how well the education matches the requirement>,
  "education_summary": "<1-2 sentences>",
  "overall_score": <0-100 overall match>,
  "confidence": "low" or "medium" or "high",
  "summary": "<2-3 sentence overall assessment>"
}
The "skills" list must contain one entry for EVERY must-have and preferred skill provided.
For each skill marked present, provide a short exact excerpt showing how the candidate used or listed the skill. Do not invent or paraphrase evidence.
If supporting evidence cannot be provided, leave evidence empty. Missing evidence will earn no skill points, but will not reject the whole resume."""

    API_URL = "https://openrouter.ai/api/v1"
    MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"

    # constructor
    def __init__(self, api_url=None, model_name=None):
        load_dotenv()
        self.api_url = api_url or os.environ.get("OPENROUTER_API_URL") or self.API_URL
        self.model_name = model_name or os.environ.get("OPENROUTER_MODEL") or self.MODEL_NAME
        self.client = self._create_client()

    # load openrouter api key from env
    def _load_api_key(self):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("API key not found in environment variables")
        return api_key

    # get openAI client
    def _get_client(self, api_url, api_key):
        return OpenAI(
            base_url=api_url,
            api_key=api_key,
            # max time before stopping
            timeout=60,
            # auto retry 429 (rate limit errors) and 5xx (server errors)
            max_retries=3,
        )

    # create the client to reuse
    def _create_client(self):
        api_key = self._load_api_key()
        return self._get_client(self.api_url, api_key)

    # read a field from either a typed Job object or a plain dict
    @staticmethod
    def _read_job_field(job_description, field, default=""):
        if isinstance(job_description, dict):
            return job_description.get(field, default)
        return getattr(job_description, field, default)

    # build the user prompt
    def _build_user_prompt(self, job_description, resume_text):
        title = self._read_job_field(job_description, "title", "")
        required_skills = self._read_job_field(job_description, "required_skills", []) or []
        preferred = self._read_job_field(job_description, "preferred", []) or []
        min_experience = self._read_job_field(job_description, "min_experience", 0)
        education = self._read_job_field(job_description, "education", "")
        return (
            "JOB TITLE:\n" + str(title) + "\n\n"
            "MUST-HAVE SKILLS:\n" + ", ".join(required_skills) + "\n\n"
            "PREFERRED SKILLS:\n" + ", ".join(preferred) + "\n\n"
            "MINIMUM YEARS OF EXPERIENCE:\n" + str(min_experience) + "\n\n"
            "EDUCATION REQUIREMENT:\n" + str(education) + "\n\n"
            "ANONYMISED RESUME TEXT:\n" + str(resume_text)
        )

    # strip optional markdown code fences if the model wrapped its JSON reply
    @staticmethod
    def _strip_code_fences(content):
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                return "\n".join(lines[1:-1]).strip()
        return stripped

    # check the reply
    def _parse_response(self, response):
        # Pull the JSON result out of an API response. Raises ValueError if malformed
        try:
            if not response.choices:
                raise ValueError("response contained no choices")
            content = response.choices[0].message.content
            if not content or not isinstance(content, str):
                raise ValueError("response was empty")
            cleaned = self._strip_code_fences(content)
            # JSONDecodeError is a kind of ValueError, so it is caught below too
            return self._validate_ai_result(json.loads(cleaned))
        except (AttributeError, IndexError, TypeError, ValueError) as e:
            raise ValueError(f"Malformed API response: {e}") from e

    # validate json data and check right values
    def _validate_ai_result(self, data):
        # check the data has all the fields the logic manager needs
        if not isinstance(data, dict):
            raise ValueError("reply must be a JSON object")

        required_fields = [
            "skills",
            "experience_score",
            "education_score",
            "overall_score",
            "confidence",
        ]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"missing field '{field}'")

        if not isinstance(data["skills"], list):
            raise ValueError("'skills' must be a list")

        # Missing evidence is allowed but malformed skill entries are not.
        for skill in data["skills"]:
            if not isinstance(skill, dict):
                raise ValueError("each skill must be a JSON object")
            if not isinstance(skill.get("name"), str) or not skill["name"].strip():
                raise ValueError("each skill must have a nonempty name")
            if skill.get("category") not in ("must_have", "preferred"):
                raise ValueError("skill category must be must_have or preferred")
            if not isinstance(skill.get("present"), bool):
                raise ValueError("skill present must be true or false")
            last_used_year = skill.get("last_used_year")
            if last_used_year is not None and (
                isinstance(last_used_year, bool) or not isinstance(last_used_year, int)
            ):
                raise ValueError("skill last_used_year must be an integer or null")
            evidence = skill.get("evidence")
            if evidence is not None and not isinstance(evidence, str):
                raise ValueError("skill evidence must be text or null")

        for field in ("experience_score", "education_score", "overall_score"):
            score = data[field]
            if (
                isinstance(score, bool)
                or not isinstance(score, (int, float))
                or not math.isfinite(score)
                or not 0 <= score <= 100
            ):
                raise ValueError(f"'{field}' must be a number from 0 to 100")

        if data["confidence"] not in ("low", "medium", "high"):
            raise ValueError("invalid confidence value")

        return data

    # describe API call errors
    def _api_error_description(self, error):
        # return user-friendly message for any OpenAI API exceptions

        # Order is important - APITimeoutError is a subclass of APIConnectionError
        if isinstance(error, openai.APITimeoutError):
            return "The API request timed out. The service may be slow or unavailable; try again later."
        elif isinstance(error, openai.APIConnectionError):  # elif not needed but kept for readability
            return "Could not connect to the API. Check your internet connection."
        elif isinstance(error, openai.RateLimitError):
            return "The API rate limit was reached. Wait a moment, then retry."
        elif isinstance(error, openai.InternalServerError):
            return "The API service is currently unavailable. Try again later."
        elif isinstance(error, (openai.AuthenticationError, openai.PermissionDeniedError)):
            return "The API key was rejected. Check OPENROUTER_API_KEY in your .env file."
        elif isinstance(error, openai.NotFoundError):
            return "The AI model was not found. It may no longer be available; check MODEL_NAME."
        return f"The API rejected the request: {error}"

    # check for errors that you can retry
    def _can_retry_error(self, error):
        # only true for temporary problems (connection, timeout, rate limit, server error)
        return isinstance(
            error,
            (
                openai.APIConnectionError,
                openai.APITimeoutError,
                openai.RateLimitError,
                openai.InternalServerError,
            ),
        )

    # make the api call
    def _ai_processing(self, system_prompt, user_prompt):
        # call the model and return validated dictionary
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )
            # includes timeouts
        except openai.OpenAIError as e:
            # OpenAI SDK already retried the errors worth retrying
            error_msg = self._api_error_description(e)

            # check if error can be retried
            if self._can_retry_error(e):
                raise ConnectionError(error_msg)
            raise ValueError(f"API request failed: {error_msg}")

        return self._parse_response(response)

    # main method for API
    def process_resume(self, job_description, resume_text):
        # calls API and screens the resume and returns validated data else raise error
        user_prompt = self._build_user_prompt(job_description, resume_text)
        return self._ai_processing(self.SYSTEM_PROMPT, user_prompt)
