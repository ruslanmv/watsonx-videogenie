"""Prompt Service Main Module.

This FastAPI service transforms raw text into timed script segments using IBM Watson X.
It leverages Granite foundation models for intelligent script processing and time prediction.

Author: Ruslan Magana (https://ruslanmv.com)
License: Apache 2.0
"""

import logging
import os
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, status
from ibm_watsonx_ai import IAMTokenManager
from ibm_watsonx_ai.foundation_models import Model
from pydantic import BaseModel, Field, validator

from utils import split_sentences

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# IBM Watson X Configuration
APIKEY = os.environ.get("WATSONX_APIKEY")
PROJECT_ID = os.environ.get("PROJECT_ID")
MODEL_ID = os.getenv("MODEL_ID", "granite-13b-chat-v2")
SERVICE_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

# Validate required environment variables
if not APIKEY:
    logger.error("WATSONX_APIKEY environment variable not set")
    raise EnvironmentError("WATSONX_APIKEY is required")

if not PROJECT_ID:
    logger.error("PROJECT_ID environment variable not set")
    raise EnvironmentError("PROJECT_ID is required")

# Initialize Watson X AI components
try:
    token_manager = IAMTokenManager(
        api_key=APIKEY,
        url=f"{SERVICE_URL}/oidc/token",
    )

    model = Model(
        model_id=MODEL_ID,
        project_id=PROJECT_ID,
        credentials={"token_manager": token_manager},
    )
    logger.info(f"Successfully initialized Watson X model: {MODEL_ID}")

except Exception as e:
    logger.error(f"Failed to initialize Watson X: {e}")
    raise RuntimeError(f"Watson X initialization failed: {str(e)}")


# Pydantic Models
class PromptRequest(BaseModel):
    """Request model for prompt processing.

    Attributes:
        text: Raw input text to be processed and segmented.
    """

    text: str = Field(
        ...,
        description="Input text to process into timed script segments",
        min_length=5,
        max_length=50000,
    )

    @validator("text")
    def validate_text(cls, v: str) -> str:
        """Validate text is not empty or whitespace only.

        Args:
            v: Input text value.

        Returns:
            Validated text.

        Raises:
            ValueError: If text is empty or too short.
        """
        if not v or len(v.strip()) < 5:
            raise ValueError("Text must be at least 5 characters long")
        return v.strip()


class ScriptSegment(BaseModel):
    """Individual script segment with timing.

    Attributes:
        text: Segment text content.
        seconds: Predicted speaking duration in seconds.
    """

    text: str = Field(..., description="Segment text content")
    seconds: float = Field(..., description="Predicted speaking time in seconds", gt=0)


class PromptResponse(BaseModel):
    """Response model for processed prompts.

    Attributes:
        segments: List of timed script segments or raw response.
        total_duration: Total predicted speaking duration (optional).
    """

    segments: Any = Field(..., description="Processed script segments")
    total_duration: float | None = Field(
        None,
        description="Total predicted duration in seconds",
    )


# Initialize FastAPI application
app = FastAPI(
    title="Prompt Service",
    description="Watson X powered script processing and time prediction service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """Health check endpoint.

    Returns:
        Dict containing health status and model information.
    """
    return {
        "status": "healthy",
        "service": "prompt-service",
        "model": MODEL_ID,
    }


@app.post("/prompt", response_model=PromptResponse, status_code=status.HTTP_200_OK)
async def process_prompt(body: PromptRequest) -> Dict[str, Any]:
    """Process text prompt using Watson X Granite model.

    Transforms raw text into timed script segments with predicted speaking duration
    for each sentence. Uses IBM Watson X foundation models for intelligent analysis.

    Args:
        body: PromptRequest containing the text to process.

    Returns:
        Dict containing processed segments with timing information.

    Raises:
        HTTPException: If Watson X API fails or text processing encounters errors.
    """
    try:
        logger.info(f"Processing prompt with {len(body.text)} characters")

        # Split text into sentences
        sentences = split_sentences(body.text)
        logger.info(f"Split into {len(sentences)} sentences")

        if not sentences:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract sentences from text",
            )

        # Construct Watson X prompt
        system_prompt = (
            "You are a presentation script assistant. "
            "Analyze the provided text and return a JSON array with timing predictions. "
            "Each element should have: {\"text\": \"sentence\", \"seconds\": predicted_duration}. "
            "Estimate speaking time at normal pace (150 words per minute). "
            "Return ONLY valid JSON, no additional text or markdown."
        )

        user_content = "\n".join(sentences)

        # Generate response using Watson X
        logger.info("Calling Watson X Granite model")

        try:
            response = model.generate_text(
                prompt=system_prompt,
                input=user_content,
                params={
                    "max_new_tokens": 2048,
                    "temperature": 0.2,
                    "decoding_method": "greedy",
                    "repetition_penalty": 1.0,
                },
            )

            logger.info("Successfully received Watson X response")

            return {
                "segments": response,
                "total_duration": None,  # Could be calculated if response is parsed
            }

        except Exception as watson_error:
            logger.error(f"Watson X API error: {watson_error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Watson X service error: {str(watson_error)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process prompt: {str(e)}",
        )


@app.on_event("startup")
async def startup_event() -> None:
    """Application startup event handler.

    Logs configuration and validates Watson X connection.
    """
    logger.info("Starting Prompt Service")
    logger.info(f"Watson X Model: {MODEL_ID}")
    logger.info(f"Watson X URL: {SERVICE_URL}")
    logger.info(f"Project ID: {PROJECT_ID[:8]}...")  # Log only first 8 chars for security


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Application shutdown event handler."""
    logger.info("Shutting down Prompt Service")
