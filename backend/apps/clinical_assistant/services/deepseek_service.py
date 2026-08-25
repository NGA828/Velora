from __future__ import annotations

import logging
import os
from typing import Any
import requests

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = (
    "The conversational assistant is temporarily unavailable. "
    "Please refer to the Clinical Decision Support recommendation on the dashboard "
    "and contact the attending medical team for further assistance."
)


class DeepSeekService:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int = 20,
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")).rstrip("/")
        self.timeout = timeout

    def generate_chat_response(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        """
        Calls DeepSeek Chat Completions API with fallback protection.
        Returns a dict:
        {
            "success": bool,
            "content": str,
            "error": str | None,
            "fallback": bool,
            "usage": dict | None,
        }
        """
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY is not configured. Returning fallback message.")
            return {
                "success": False,
                "content": FALLBACK_MESSAGE,
                "error": "DEEPSEEK_API_KEY_NOT_CONFIGURED",
                "fallback": True,
                "usage": None,
            }

        payload_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            if msg.get("role") in {"user", "assistant"}:
                payload_messages.append({"role": msg["role"], "content": msg["content"]})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        endpoint = f"{self.base_url}/chat/completions"

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json={
                    "model": self.model,
                    "messages": payload_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=self.timeout,
            )

            if response.status_code != 200:
                logger.error(
                    "DeepSeek API returned error status %s: %s",
                    response.status_code,
                    response.text[:200],
                )
                return {
                    "success": False,
                    "content": FALLBACK_MESSAGE,
                    "error": f"HTTP_{response.status_code}: {response.text[:200]}",
                    "fallback": True,
                    "usage": None,
                }

            data = response.json()
            choices = data.get("choices", [])
            if not choices or not choices[0].get("message", {}).get("content"):
                logger.error("DeepSeek API returned empty choices or missing content: %s", data)
                return {
                    "success": False,
                    "content": FALLBACK_MESSAGE,
                    "error": "EMPTY_RESPONSE",
                    "fallback": True,
                    "usage": None,
                }

            content = choices[0]["message"]["content"].strip()
            return {
                "success": True,
                "content": content,
                "error": None,
                "fallback": False,
                "usage": data.get("usage"),
            }

        except requests.Timeout as exc:
            logger.error("DeepSeek API timed out: %s", exc)
            return {
                "success": False,
                "content": FALLBACK_MESSAGE,
                "error": "TIMEOUT",
                "fallback": True,
                "usage": None,
            }
        except requests.RequestException as exc:
            logger.error("DeepSeek API network/request error: %s", exc)
            return {
                "success": False,
                "content": FALLBACK_MESSAGE,
                "error": str(exc),
                "fallback": True,
                "usage": None,
            }
        except Exception as exc:
            logger.error("Unexpected error calling DeepSeek API: %s", exc)
            return {
                "success": False,
                "content": FALLBACK_MESSAGE,
                "error": str(exc),
                "fallback": True,
                "usage": None,
            }


deepseek_service = DeepSeekService()
