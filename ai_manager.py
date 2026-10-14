import json
import os
import openai
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

# API URL
API_URL = "https://openrouter.ai/api/v1"
# Model Name
MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"

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

# create the client to reuse
def create_client():
    api_key = load_api_key()
    return get_client(API_URL, api_key)

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

# check the reply
def parse_response(response):
    # Pull the JSON result out of an API response. Raises ValueError if malformed
    try:
        if not response.choices:
            raise ValueError("response contained no choices")
        content = response.choices[0].message.content
        if not content:
            raise ValueError("response was empty")
        # JSONDecodeError is a kind of ValueError, so it is caught below too
        return validate_ai_result(json.loads(content))
    except (AttributeError, IndexError, TypeError, ValueError) as e:
        raise ValueError(f"Malformed API response: {e}") from e


# validate json data and check right values
def validate_ai_result(data):
    # check the data has all teh fields the logic manager needs
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

    # Missing evidence is allowed; malformed skill entries are not.
    for skill in data["skills"]:
        if not isinstance(skill, dict):
            raise ValueError("each skill must be a JSON object")
        if not isinstance(skill.get("name"), str) or not skill["name"].strip():
            raise ValueError("each skill must have a nonempty name")
        if skill.get("category") not in ("must_have", "preferred"):
            raise ValueError("skill category must be must_have or preferred")
        if not isinstance(skill.get("present"), bool):
            raise ValueError("skill present must be true or false")
        evidence = skill.get("evidence")
        if evidence is not None and not isinstance(evidence, str):
            raise ValueError("skill evidence must be text or null")
 
    for field in ("experience_score", "education_score", "overall_score"):
        score = data[field]
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not 0 <= score <= 100
        ):
            raise ValueError(f"'{field}' must be a number from 0 to 100")
 
    if data["confidence"] not in ("low", "medium", "high"):
        raise ValueError("invalid confidence value")
 
    return data


# describe API call errors
def api_error_description(error):
    # return user-friendly message for any OpenAI API excepions

    # Order is important - APITimeoutErrro is a subclass of APIConnectionError
    if isinstance(error, openai.APITimeoutError):
        return "The API request timed out. The service may be slow or unavailable; try again later."
    elif isinstance(error, openai.APIConnectionError): # elif is not needed but added for readability as its an early return
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

# check for erorrs that you can retry
def can_retry_error(error):
    # only true for temporary problems (connection, timeout, rate limit, server erorr)
    return isinstance(error, (openai.APIConnectionError, 
                              openai.APITimeoutError, 
                              openai.RateLimitError, 
                              openai.InternalServerError))

# make the api call
def ai_processing(client, system_prompt, user_prompt):
    # call the model and return validated dictionary
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        # includes timeouts
    except openai.OpenAIError as e:
        # OpenAI SDK already retried the errors worth retrying
        error_msg = api_error_description(e)

        # check if error can be retried
        if can_retry_error(e):
            # Log the error and retry logic would go here
            raise ConnectionError(error_msg)
        raise ValueError(f"API request failed: {error_msg}")
 
    return parse_response(response)



# main function for API
def process_resume_ai(client, job_description, resume_text):
    # calls API and screens each resume and returns validated data else raise error
    user_prompt = build_user_prompt(job_description, resume_text)
    return ai_processing(client, SYSTEM_PROMPT, user_prompt)
