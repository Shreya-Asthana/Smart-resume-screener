# llm_client.py
import os
import requests
import json

# Make sure these environment variables are set
GROQ_API_KEY = os.getenv("LLM_API_KEY")
GROQ_API_URL = os.getenv("LLM_API_URL")
GROQ_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

def build_prompt(resume_skills_text: str, job_desc: str) -> str:
    """
    Build a prompt for Groq LLM using candidate Skills section + Job Description.
    LLM should return JSON: score (1-10), justification, matches, recommendation
    """
    prompt = (
        "You are a technical recruiter. Compare the candidate's Skills section "
        "with the Job Description and evaluate fit.\n\n"
        "Return ONLY JSON in the following format:\n"
        '{"score": <float>, "justification": <string>, "matches": [<skills>], "recommendation": <string>}\n\n'
        "Job Description:\n" + job_desc + "\n\n" +
        "Candidate Skills Section:\n" + resume_skills_text
    )
    return prompt

def call_llm_groq(prompt: str, max_tokens: int = 300) -> str:
    """
    Call Groq API (OpenAI-compatible Chat Completions) and return LLM output text.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY environment variable not set.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()

    # Extract output text
    try:
        text = data["choices"][0]["message"]["content"]
        return text
    except (KeyError, IndexError):
        return json.dumps(data)

def rate_candidate(skills_section_text: str, job_desc: str) -> dict:
    """
    Rates candidate against job description using Groq LLM.
    Returns structured dict with score, justification, matches, recommendation.
    """
    prompt = build_prompt(skills_section_text, job_desc)
    llm_output = call_llm_groq(prompt)

    # Attempt to parse JSON returned by LLM
    try:
        parsed = json.loads(llm_output)
        # Ensure required keys exist
        for key in ["score", "justification", "matches", "recommendation"]:
            if key not in parsed:
                parsed[key] = "" if key != "score" else 0.0
        return parsed
    except Exception:
        # If parsing fails, return raw text with score=0
        return {
            "score": 0.0,
            "justification": llm_output,
            "matches": [],
            "recommendation": ""
        }
