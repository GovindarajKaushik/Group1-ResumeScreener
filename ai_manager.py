from os import getenv
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=getenv("OPENROUTER_API_KEY"),
)


# First APi call with reasoning
response = client.chat.completions.create(
    model="nvidia/nemotron-3-ultra-550b-a55b:free",
    messages=[
        {
            "role":"user",
            "content":"What is the capital of France?"
        }
    ],
)

response = response.choices[0].message
print(response)