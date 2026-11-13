"""Provider and replay adapters. Logs contain synthetic material, never credentials."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BUILD_MODEL = "qwen/qwen3.8-27b"
REVIEW_MODEL = "qwen/qwen3.6-35b-a3b"


class ModelError(RuntimeError):
    pass


class OpenRouter:
    mode = "live"

    def __init__(self, key, build_model=BUILD_MODEL, review_model=REVIEW_MODEL):
        if not key:
            raise ValueError("Set OPENROUTER_API_KEY for live runs")
        self.key = key
        self.models = {"build": build_model, "review": review_model}

    @classmethod
    def from_env(cls):
        return cls(os.getenv("OPENROUTER_API_KEY"), os.getenv("BUILD_MODEL", BUILD_MODEL),
                   os.getenv("REVIEW_MODEL", REVIEW_MODEL))

    def __call__(self, stage, messages, timeout):
        payload = {"model": self.models["build" if stage == "prompt" else stage], "messages": messages, "temperature": 0,
                   "max_tokens": 2200, "reasoning": {"enabled": False},
                   "response_format": {"type": "json_object"}}
        request = Request("https://openrouter.ai/api/v1/chat/completions",
                          json.dumps(payload).encode(), {
                              "Authorization": "Bearer " + self.key,
                              "Content-Type": "application/json",
                          })
        try:
            with urlopen(request, timeout=timeout) as response:
                result = json.load(response)
            choice = result["choices"][0]
            content = choice["message"]["content"]
            return {"model": result.get("model", payload["model"]), "provider": result.get("provider"),
                    "response_id": result.get("id"), "finish_reason": choice.get("finish_reason"),
                    "usage": result.get("usage"), "raw_output": content,
                    "request_config": {k: v for k, v in payload.items() if k != "messages"}}
        except HTTPError as error:
            raise ModelError(f"OpenRouter HTTP {error.code}") from None
        except (URLError, OSError, ValueError, KeyError, IndexError, TypeError) as error:
            raise ModelError(f"OpenRouter response unavailable: {type(error).__name__}") from None


class Replay:
    mode = "replay"

    def __init__(self, entries):
        self.entries = iter(entries)

    def __call__(self, stage, messages, timeout):
        entry = next(self.entries, None)
        if not entry or entry["stage"] != stage or entry["messages"] != messages:
            raise ModelError("Replay stage or exact prompt differs from recorded run")
        if entry.get("error"):
            raise ModelError(entry["error"])
        return entry["response"]
