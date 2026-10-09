import json
import os
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


def load_api_key():
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("API key not found in environment variables")
        return api_key
    except Exception as e:
        raise ValueError(f"Error loading API client: {e}")

def get_client(API_URL, API_KEY):
    return OpenAI(
        base_url=API_URL,
        api_key=API_KEY
    )


def ai_processing(client, system_prompt, user_prompt):
    # API call
    response = client.chat.completions.create(
        model="apodex/apodex-1.1-mini:free",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0
    )

    # save valid output to variable
    content = response.choices[0].message.content

    if not content:
        raise ValueError("The API returned an empty response")

    # Check if AI returned valid json output
    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response from AI model: {e}")
    return result

# main function for API
def process_resume_ai(user_prompt):
    try:
        ai_api_url = "https://openrouter.ai/api/v1"
        api_key = load_api_key()
        client = get_client(ai_api_url, api_key)
        result = ai_processing(client, SYSTEM_PROMPT, user_prompt)
        return result
    except ValueError as e:
        raise ValueError(f"Error in ai_manager: {e}")