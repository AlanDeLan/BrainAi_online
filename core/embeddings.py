from typing import List, Optional
from core.ai_providers import get_current_provider, get_provider_config, AIProvider

EMBED_DIM = 768  # Target dimension for Google text-embedding-004


def embed_text(text: str) -> Optional[List[float]]:
    """
    Compute embedding for text using the configured provider.
    Prefer Google text-embedding-004 (768d) to match pgvector schema.
    Returns list of floats or None on failure.
    """
    provider = get_current_provider()
    config = get_provider_config()

    # Prefer Google embeddings to ensure 768-dim compatibility
    try:
        if provider == AIProvider.GOOGLE_AI and config.get("google_api_key"):
            return _embed_google(text, config["google_api_key"])  # type: ignore
        # If provider is OpenAI but Google key exists, still use Google for fixed dim
        if config.get("google_api_key"):
            return _embed_google(text, config["google_api_key"])  # type: ignore
    except Exception:
        pass

    # Fallback: try OpenAI if available (dimension may not match schema)
    try:
        if provider == AIProvider.OPENAI and config.get("openai_api_key"):
            vec = _embed_openai(text, config.get("openai_api_key"), config.get("openai_base_url"))
            # If dimension mismatches, return None to avoid DB errors
            if vec is not None and len(vec) == EMBED_DIM:
                return vec
            return None
    except Exception:
        return None

    return None


def _embed_google(text: str, api_key: str) -> Optional[List[float]]:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    try:
        res = genai.embed_content(model="models/text-embedding-004", content=text)
        # API may return dict with 'embedding' key
        embedding = res.get("embedding") if isinstance(res, dict) else getattr(res, "embedding", None)
        if embedding and isinstance(embedding, list):
            return [float(x) for x in embedding]
    except Exception:
        return None
    return None


def _embed_openai(text: str, api_key: str, base_url: Optional[str] = None) -> Optional[List[float]]:
    try:
        from openai import OpenAI
    except ImportError:
        return None
    try:
        client = OpenAI(api_key=api_key, base_url=base_url or "https://api.openai.com/v1")
        resp = client.embeddings.create(model="text-embedding-3-small", input=text)
        if resp and resp.data and resp.data[0].embedding:
            return [float(x) for x in resp.data[0].embedding]
    except Exception:
        return None
    return None
