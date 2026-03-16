# groq_client.py
from groq import Groq
import os
import logging
from dotenv import load_dotenv
from typing import Optional, Any
import inspect
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

logger = logging.getLogger(__name__)

load_dotenv()

_client: Optional[Groq] = None

def _get_client() -> Groq:
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set. Add it to .env or export it in your shell.")
    _client = Groq(api_key=api_key)
    return _client

def _choose_token_param(func) -> Optional[str]:
    """
    Inspect the signature of the SDK function and return which
    keyword name to use for token limit, or None if none supported.
    """
    try:
        sig = inspect.signature(func)
        params = sig.parameters.keys()
        if "max_output_tokens" in params:
            return "max_output_tokens"
        if "max_tokens" in params:
            return "max_tokens"
    except Exception:
        # If inspection fails, return None and we'll try calls without token param
        pass
    return None

def _extract_text_from_response(resp: Any) -> str:
    """
    Try multiple common response shapes to extract generated text.
    """
    try:
        # typical shape: resp.choices[0].message.content
        return resp.choices[0].message.content
    except Exception:
        pass
    try:
        # alternative: resp.choices[0].text
        return resp.choices[0].text
    except Exception:
        pass
    try:
        # Groq older/newer shapes
        # e.g., resp.output[0].content[0].text
        return resp.output[0].content[0].text
    except Exception:
        pass
    # fallback to string representation
    try:
        return str(resp)
    except Exception as e:
        return f"[error extracting text: {e}]"

def _call_gemini_fallback(prompt: str) -> str:
    """Fallback logic utilizing the Google Gemini SDK when Groq fails."""
    try:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "[error: Groq failed and GEMINI_API_KEY is missing for fallback]"
            
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"[error: both Groq and Gemini fallback failed: {e}]"

def ask_groq(prompt: str,
             model: str = "openai/gpt-oss-120b",
             temperature: float = 0.7,
             max_tokens: Optional[int] = None) -> str:
    """
    Safe, adaptive Groq wrapper. Accepts `max_tokens` for compatibility and
    maps it to the appropriate SDK parameter if supported.
    Returns generated text string or an error marker starting with '[error:'.
    
    If Groq fails (e.g., HTTP 429 or 500 timeout), it will automatically
    failover to Gemini flash.
    """
    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def _execute():
        client = _get_client()
        func = client.chat.completions.create
        token_param_name = _choose_token_param(func)

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a professional AI research assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": float(temperature)
        }

        # Add token param only if we detected a supported name
        if max_tokens is not None and token_param_name:
            payload[token_param_name] = int(max_tokens)

        # Try calling once with chosen payload
        resp = func(**payload)
        return _extract_text_from_response(resp)

    try:
        return _execute()
    except Exception as groq_error:
        # If Groq fails for any reason (Rate Limit, Server Timeout, Bad Request)
        # Attempt to failover to Gemini
        logger.warning(f"⚠️ Groq failed after retries: {groq_error}. Attempting Gemini failover...")
        return _call_gemini_fallback(prompt)
