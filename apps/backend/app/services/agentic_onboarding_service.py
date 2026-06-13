import json
import logging
import os
from typing import Any

from litellm import completion  # type: ignore

logger = logging.getLogger("profmatch.agentic_onboarding")


def _get_model() -> str:
    model_name = os.environ.get("OPENROUTER_MODEL", "inclusionai/ring-2.6-1t:free").strip()
    if not model_name.startswith("openrouter/"):
        model_name = f"openrouter/{model_name}"
    return model_name


def _call_llm(prompt: str, is_json: bool = True) -> Any:
    model = _get_model()
    try:
        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            # Drop response_format to support models like tencent/hy3-preview:free
        )
        content = response.choices[0].message.content or ""

        if is_json:
            try:
                # Clean up markdown fences if present
                content = content.strip()
                if content.startswith("```json"):
                    content = content.replace("```json", "", 1)
                elif content.startswith("```"):
                    content = content.replace("```", "", 1)
                if content.endswith("```"):
                    content = content[:-3]

                # Attempt to parse json, with a bit of recovery if the model
                # returned something weird around the JSON object.
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    content = content[start_idx:end_idx + 1]

                return json.loads(content.strip())
            except Exception as json_e:
                logger.error(f"Failed to parse JSON. Raw content: {content}")
                raise json_e
        return content
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise
