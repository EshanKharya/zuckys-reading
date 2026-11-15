import os
from typing import Dict, Any, Optional
import config

def load_prompt_template(prompt_name: str, **kwargs: Any) -> str:
    """
    Loads an editable markdown prompt template from config.PROMPTS_DIR.
    Optionally formats the template with kwargs.
    """
    file_name = f"{prompt_name}.md" if not prompt_name.endswith(".md") else prompt_name
    prompt_path = os.path.join(config.PROMPTS_DIR, file_name)

    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt template file not found: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        content = f.read()

    if kwargs:
        # Safe format string replacement
        for key, val in kwargs.items():
            placeholder = f"{{{key}}}"
            content = content.replace(placeholder, str(val))

    return content
