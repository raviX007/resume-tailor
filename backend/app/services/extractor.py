"""Step 1: LLM parses JD to extract structured keywords.

Fetches prompt from Langfuse ("resume-tailor-extract") at runtime.
Prompt managed in Langfuse — edit via Langfuse UI, push via scripts/push_prompts.py.
"""

from app.core.langfuse_client import get_prompt_messages, observe
from app.core.llm import get_llm_client
from app.core.constants import JD_TRUNCATE_LENGTH
from app.core.logger import logger
from app.models import ExtractedKeywords


@observe(name="resume-tailor-extract")
async def extract_keywords(jd_text: str, job_title: str = "") -> ExtractedKeywords | None:
    """Extract structured keywords from a job description via LLM.

    Fetches prompt from Langfuse ("resume-tailor-extract").
    Returns ExtractedKeywords or None if LLM call fails.
    """
    truncated_jd = jd_text[:JD_TRUNCATE_LENGTH]

    template_vars = {
        "jd_text": truncated_jd,
        "job_title": job_title,
    }

    default_config = {"temperature": 0.1, "max_tokens": 1000}

    langfuse_result = get_prompt_messages("resume-tailor-extract", template_vars)
    if langfuse_result:
        system_prompt, user_prompt, config = langfuse_result
        config = config or default_config
    else:
        from app.core.fallback_prompts import FALLBACK_PROMPTS
        fb = FALLBACK_PROMPTS["resume-tailor-extract"]
        system_prompt = fb["system"]
        user_prompt = fb["user"].format(**template_vars)
        config = fb["config"]
        logger.warning("Langfuse unavailable — using embedded fallback for resume-tailor-extract")

    llm = await get_llm_client()
    result = await llm.call_json(
        prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=config.get("temperature", 0.1),
        max_tokens=config.get("max_tokens", 1000),
        name="jd-keyword-extraction",
    )

    if not result:
        logger.warning("JD keyword extraction returned no result")
        return None

    try:
        return ExtractedKeywords(**result)
    except (KeyError, TypeError, ValueError) as e:
        logger.warning(f"Failed to parse extraction result: {e}")
        return None
