import json
import os
import time
from os import getenv
from dotenv import load_dotenv
from openai import OpenAI

# system prompt
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
     "evidence": "<short phrase from the resume that justifies this, or empty if absent>"}
  ],
  "experience_score": <0-100, how well the candidate's experience matches the role>,
  "experience_summary": "<1-2 sentences>",
  "education_score": <0-100, how well the education matches the requirement>,
  "education_summary": "<1-2 sentences>",
  "overall_score": <0-100 overall match>,
  "confidence": "low" or "medium" or "high",
  "summary": "<2-3 sentence overall assessment>"
}
The "skills" list must contain one entry for EVERY must-have and preferred skill provided."""



load_dotenv()


# load openrouter api key from env
def load_api_key():
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("API key not found in environment variables")
        return api_key
    except Exception as e:
        raise ValueError(f"Error loading API client: {e}")

# get openAI client
def get_client(api_url, api_key):
    return OpenAI(
        base_url=api_url,
        api_key=api_key,
        # max time before stopping
        timeout=60,
        # auto retry 429 (rate limit errors) and 5xx (server errors)
        max_retries=3
    )

# build the user prompt
def build_user_prompt(job_description, resume_text):
    return (
        "JOB TITLE:\n" + str(job_description.get("title", "")) + "\n\n"
        "MUST-HAVE SKILLS:\n" + ", ".join(job_description.get("required_skills", [])) + "\n\n"
        "PREFERRED SKILLS:\n" + ", ".join(job_description.get("preferred", [])) + "\n\n"
        "MINIMUM YEARS OF EXPERIENCE:\n" + str(job_description.get("min_experience", 0)) + "\n\n"
        "EDUCATION REQUIREMENT:\n" + str(job_description.get("education", "")) + "\n\n"
        "ANONYMISED RESUME TEXT:\n" + resume_text
    )


# validate json data and check right values
def validate_ai_result(raw_response):
    """Parse the AI response and check essential fields."""
    try:
        data = json.loads(raw_response)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("AI returned invalid JSON.")

    if not isinstance(data, dict):
        raise ValueError("AI response must be a JSON object.")

    required_fields = [
        "skills",
        "experience_score",
        "education_score",
        "overall_score",
        "confidence",
    ]

    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    if not isinstance(data["skills"], list):
        raise ValueError("'skills' must be a list.")

    for field in (
        "experience_score",
        "education_score",
        "overall_score",
    ):
        score = data[field]

        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not 0 <= score <= 100
        ):
            raise ValueError(
                f"'{field}' must be a number from 0 to 100."
            )

    if data["confidence"] not in ("low", "medium", "high"):
        raise ValueError("Invalid confidence value.")

    return data


# make the api call
def ai_processing(client, system_prompt, user_prompt, attempts=3):
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            response = client.chat.completions.create(
                model="apodex/apodex-1.1-mini:free",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("The API returned an empty response")

            return json.loads(content)

        except (OpenAI.AuthenticationError, OpenAI.PermissionDeniedError,
                OpenAI.BadRequestError, OpenAI.NotFoundError) as e:
            # permanent errors: retrying won't help
            raise ValueError(f"Non-retryable API error: {e}")

        except (OpenAI.RateLimitError, OpenAI.APITimeoutError,
                OpenAI.APIConnectionError, OpenAI.InternalServerError,
                json.JSONDecodeError, ValueError) as e:
            # transient errors or bad model output: retry
            last_error = e
            if attempt < attempts:
                time.sleep(2 ** attempt)  # waits 2s, then 4s

    raise ValueError(f"Failed after {attempts} attempts: {last_error}")




# main function for API
def process_resume_ai(user_prompt):
    try:
        ai_api_url = "https://openrouter.ai/api/v1"
        api_key = load_api_key()
        client = get_client(ai_api_url, api_key)
        result = ai_processing(client, SYSTEM_PROMPT, user_prompt)
        return result
    except Exception as e:
        raise ValueError(f"Error in ai_manager: {e}")