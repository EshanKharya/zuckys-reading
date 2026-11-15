import json
import re
import sys
from typing import Optional, Dict, Any
import requests

import config
from src.llm.base import BaseLLMClient

def _clean_json_string(raw: str) -> str:
    """Strips markdown code fences and whitespace from raw LLM responses."""
    cleaned = raw.strip()
    # Remove leading ```json or ```
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    # Remove trailing ```
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()

class OllamaClient(BaseLLMClient):
    """Client for local Ollama server running models like qwen2.5:7b-instruct."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        context_window: Optional[int] = None,
        timeout: int = 120,
    ):
        self.base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or config.MODEL_NAME
        self.temperature = temperature if temperature is not None else config.MODEL_TEMPERATURE
        self.context_window = context_window or config.MODEL_CONTEXT_WINDOW
        self.timeout = timeout

    def health_check(self) -> bool:
        """Checks if local Ollama server is responding."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: Optional[float] = None,
    ) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
                "num_ctx": self.context_window,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt
        if json_mode:
            payload["format"] = "json"

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"[!] Failed to connect to Ollama at {self.base_url}.\n"
                f"    Please ensure Ollama is installed and running (`ollama serve`)."
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"[!] Ollama generation error: {e}")

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        raw_text = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=True,
            temperature=temperature,
        )
        cleaned = _clean_json_string(raw_text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse LLM output as JSON: {e}\nRaw output:\n{raw_text[:500]}"
            )

class MockLLMClient(BaseLLMClient):
    """Mock client for offline testing and development without a running GPU service."""

    def __init__(self, *args, **kwargs):
        pass

    def health_check(self) -> bool:
        return True

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: Optional[float] = None,
    ) -> str:
        return '{"status": "mock_response"}'

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        return {
            "event_id": "E1",
            "event_name": "The Mock Event on 15 Nov 2026",
            "impact_strength": 5,
            "involvement_scores": {"%U1%": 6, "%U2%": 4},
            "topics": ["Testing", "Development"],
            "what_happened": "A mock conversation occurred.",
            "who_said_what": "%U1% talked to %U2%.",
            "hot_takes": "None",
            "singling_out": "None",
            "banter_analysis": "Playful sparring.",
            "emotional_disturbances": "None",
            "notable_quotes": ['"Testing works" - %U1%'],
        }

def get_llm_client(provider: Optional[str] = None) -> BaseLLMClient:
    """
    Factory function returning the configured LLM client instance.
    Changing models or providers requires zero edits to orchestration or agent code.
    """
    selected_provider = (provider or config.LLM_PROVIDER).strip().lower()
    if selected_provider == "ollama":
        return OllamaClient()
    elif selected_provider in ("mock", "test"):
        return MockLLMClient()
    else:
        raise ValueError(f"Unsupported LLM provider: '{selected_provider}'. Supported: 'ollama', 'mock'.")
