from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from utils import split_sentences
from ibm_watsonx_ai.foundation_models import Model
from ibm_watsonx_ai import IAMTokenManager

APIKEY      = os.environ["WATSONX_APIKEY"]
PROJECT_ID  = os.environ["PROJECT_ID"]
MODEL_ID    = os.getenv("MODEL_ID", "granite-13b-chat-v2")
SERVICE_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

tm    = IAMTokenManager(api_key=APIKEY, url=f"{SERVICE_URL}/oidc/token")
model = Model(model_id=MODEL_ID, project_id=PROJECT_ID,
              credentials={"token_manager": tm})

class PromptBody(BaseModel):
    text: str

app = FastAPI(title="prompt-svc", version="0.1.0")

@app.post("/prompt")
async def prompt(body: PromptBody):
    if len(body.text.strip()) < 5:
        raise HTTPException(400, "text is too short")

    sentences = split_sentences(body.text)

    system_prompt  = (
        "You are a presentation script assistant. "
        "Return JSON array [{text,seconds}] predicting speaking time per sentence. "
        "Do NOT include any other keys."
    )
    user_content = "\n".join(sentences)

    response = model.generate_text(
        prompt=system_prompt,
        input=user_content,
        max_new_tokens=256,
        temperature=0.2,
    )
    return {"segments": response}
