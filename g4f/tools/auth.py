from __future__ import annotations

import os
from typing import Optional

from ..providers.types import ProviderType
from .. import debug

class AuthManager:
    """Handles API key management"""
    aliases = {
        "GeminiPro": "Gemini",
        "PollinationsAI": "Pollinations",
        "OpenaiAPI": "Openai",
        "PuterJS": "Puter",
        "Puter": "Puter",
        "Anthropic": "Anthropic",
    }

    @classmethod
    def load_api_key(cls, provider: ProviderType) -> Optional[str]:
        """Load API key from config file"""
        if not provider.needs_auth and not hasattr(provider, "login_url"):
            return None

        # Auto-load .env from current directory or parent directory
        try:
            from dotenv import load_dotenv
            load_dotenv(override=False)
            cwd_env = os.path.join(os.getcwd(), ".env")
            if os.path.exists(cwd_env):
                load_dotenv(cwd_env, override=True)
        except Exception:
            pass

        provider_name = provider.get_parent()
        env_var = f"{provider_name.upper()}_API_KEY"
        api_key = os.environ.get(env_var)
        if not api_key and provider_name in cls.aliases:
            env_var = f"{cls.aliases[provider_name].upper()}_API_KEY"
            api_key = os.environ.get(env_var)
        if not api_key:
            provider_class_name = getattr(provider, "__name__", "")
            if provider_class_name:
                api_key = os.environ.get(f"{provider_class_name.upper()}_API_KEY")

        if api_key:
            # Strip enclosing quotes or whitespace
            api_key = str(api_key).strip().strip('"').strip("'")
            debug.log(f"Loading API key for {provider_name} from environment variable {env_var}")
            return api_key
        return None
