import os
import json
import re
import logging
import urllib.parse

import boto3
import google.generativeai as genai

# ---------- AWS clients ----------
s3 = boto3.client('s3')
ssm = boto3.client('ssm')

# ---------- logging ----------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------- env ----------
TEXT_BUCKET = os.environ['TEXT_BUCKET']
FINAL_BUCKET = os.environ['FINAL_BUCKET']
API_KEY_PARAM_NAME = os.environ['GEMINI_API_KEY_PARAM_NAME']
PREFERRED_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')
FALLBACK_MODELS = ['gemini-2.0-flash', 'gemini-flash-latest']

# ---------- configure Gemini once ----------
def configure_ai_model():
    try:
        logger.info(f"Fetching API Key from SSM parameter: {API_KEY_PARAM_NAME}")
        param = ssm.get_parameter(Name=API_KEY_PARAM_NAME, WithDecryption=True)
        api_key = param['Parameter']['Value']
        genai.configure(api_key=api_key)
        logger.info("Successfully configured AI model.")
    except Exception as e:
        logger.error(f"FATAL: Could not configure AI model API Key: {e}")
        raise

def _list_available_models():
    ids = set()
    try:
        for m in genai.list_models():
            name = (m.name or '').split('/')[-1]
            methods = getattr(m, 'supported_generation_methods',
                              getattr(m, 'generation_methods', []))
            if 'generateContent' in methods:
                ids.add(name)
    except Exception as e:
        logger.warning(f"Could not list models: {e}")
    logger.info(f"Models available for generateContent: {sorted(ids)}")
    return ids

def _choose_model_id():
    available = _list_available_models()
    if PREFERRED_MODEL in available:
        return PREFERRED_MODEL
    for f in FALLBACK_MODELS:
        if f in available:
            logger.info(f"Using fallback model: {f}")
            return f
    logger.info(f"Using preferred (may 404 if unavailable): {PREFERRED_MODEL}")
    return PREFERRED_MODEL

configure_ai_model()
MODEL_ID = _choose_model_id()
MODEL = genai.GenerativeModel(MODEL_ID)

# ---------- helpers ----------
JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

def _extract_json(text: str) -> str:
    m = JSON_FENCE_RE.search(text or "")
    return (m.group(1) if m else (text or "")).strip()

# ---------- LLM calls ----------
def get_structured_flowchart_data(story_text: str) -> dict:
    prompt = f"""
System Instruction:
You are an expert system designed to analyze a story and convert it into a structured flowchart format.
Your sole output must be a single, valid JSON object representing the story's flow.
The JSON object should include:
- "diagram_type": "flowchart"
- "nodes": [{{"id":"...","label":"...","shape":"..."}}]
- "edges": [{{"from":"...","to":"...","label":"..."}}]
---
Story Input:
{story_text}
---
Expected JSON Output:
""".strip()

    logger.info("Step 1: Sending story to AI model for flowchart analysis...")
    resp = MODEL.generate_content(prompt)
    raw = getattr(resp, "text", None)
    if not raw:
        raise ValueError("Empty response from model")
    json_text = _extract_json(raw)
    try:
        data = json.loads(json_text)
    except Exception as e:
        logger.error("Failed to parse model output as JSON: %s\n---\n%s\n---", e, json_text[:2000])
        raise
    if not isinstance(data, dict):
        raise ValueError("Model output is not a JSON object")
    logger.info("Step 1: Received structured flowchart from AI model.")
    return data

def generate_new_story(original_text: str, flowchart_json: dict, user_prompt: str) -> str:
    prompt = f"""
You are a creative storyteller for children. Rewrite the story based on the user's "what if" request.
Use the provided structural flowchart of the original story as context.
Your response must ONLY be the complete, new version of the story—no preamble or epilogue.

Original Story:
---
{original_text}
---

Story Flowchart (context):
---
{json.dumps(flowchart_json, indent=2)}
---

User's "What If" Request:
---
{user_prompt}
---
""".strip()

    logger.info("Step 2: Sending flowchart and user prompt to AI model for story rewrite...")
    resp = MODEL.generate_content(prompt)
    text = getattr(resp, "text", "")
    if not text:
        raise ValueError("Model returned no text for rewritten story")
    logger.info("Step 2: Received new story from AI model.")
    return text

# ---------- handler ----------
def lambda_handler(event, context):
    """
    API Gateway -> body: {"sourceKey": "<key in TEXT_BUCKET>", "userPrompt": "<what if...>"}
    1) Read story from TEXT_BUCKET/sourceKey
    2) Build flowchart JSON with Gemini
    3) Generate rewritten story with userPrompt
    4) Save outputs to FINAL_BUCKET
    """
    try:
        logger.info(f"Received event: {event}")
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else (event.get('body') or {})
        source_key = body.get('sourceKey')
        user_prompt = body.get('userPrompt')

        if not source_key or not user_prompt:
            logger.error("Missing sourceKey or userPrompt in request body.")
            return {'statusCode': 400, 'body': json.dumps({'error': 'Missing sourceKey or userPrompt in request body.'})}

        # 1) Read original story text
        obj = s3.get_object(Bucket=TEXT_BUCKET, Key=source_key)
        story_text = obj['Body'].read().decode('utf-8')

        # 2) Get flowchart JSON
        flowchart = get_structured_flowchart_data(story_text)

        # 3) Generate new story
        new_story = generate_new_story(story_text, flowchart, user_prompt)

        # 4) Write results
        base, _ = os.path.splitext(source_key)
        flowchart_key = f"{base}.flowchart.json"
        story_key = f"{base}.rewritten.txt"

        s3.put_object(
            Bucket=FINAL_BUCKET,
            Key=flowchart_key,
            Body=json.dumps(flowchart, indent=2),
            ContentType="application/json",
        )
        s3.put_object(
            Bucket=FINAL_BUCKET,
            Key=story_key,
            Body=new_story.encode('utf-8'),
            ContentType="text/plain; charset=utf-8",
        )

        logger.info(f"Wrote s3://{FINAL_BUCKET}/{flowchart_key} and s3://{FINAL_BUCKET}/{story_key}")
        return {'statusCode': 200, 'body': json.dumps({'flowchartKey': flowchart_key, 'storyKey': story_key, 'model': MODEL_ID})}

    except Exception as e:
        logger.error(f"Request failed: {e}")
        raise
