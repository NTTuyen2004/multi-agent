"""
A simple file and in-memory based caching system to reduce redundant API calls
and data processing. It creates a unique key for each function call based on
the function's name and its arguments.
"""
import asyncio
import functools
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Callable, Coroutine

# --- Configuration ---
_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = _ROOT / ".cache"
CACHE_ENABLED = True
SESSION_CACHE: dict[str, Any] = {}

logger = logging.getLogger(__name__)

# --- Helper Functions ---

def _get_cache_key(func_name: str, *args: Any, **kwargs: Any) -> str:
    """Creates a consistent, hash-based key from the function name and its arguments."""
    # Serialize arguments to a stable JSON string
    # sort_keys=True ensures that dicts with the same keys have the same representation
    # default=str handles non-serializable objects like dataframes by converting them to strings
    try:
        # A more robust serialization for complex objects like pandas DataFrames
        args_repr = [
            arg.to_json(orient='split') if hasattr(arg, 'to_json') else arg
            for arg in args
        ]
        kwargs_repr = {
            key: value.to_json(orient='split') if hasattr(value, 'to_json') else value
            for key, value in kwargs.items()
        }
        
        payload = {
            "func": func_name,
            "args": args_repr,
            "kwargs": kwargs_repr,
        }
        serialized_args = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    except Exception:
        # Fallback for very complex, non-serializable types
        serialized_args = f"{func_name}:{str(args)}:{str(kwargs)}"

    # Use SHA256 for a reliable hash
    return hashlib.sha256(serialized_args.encode('utf-8')).hexdigest()

def _get_from_file_cache(key: str) -> Any | None:
    """Reads a result from the file-based cache."""
    if not CACHE_ENABLED:
        return None
        
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{key}.json"
    
    if cache_file.exists():
        try:
            logger.info("[Cache] HIT (file) for key: %s...", key[:10])
            return json.loads(cache_file.read_text('utf-8'))
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("[Cache] Failed to read from file cache for key %s: %s", key, e)
            return None
    return None

def _save_to_file_cache(key: str, data: Any) -> None:
    """Saves a result to the file-based cache."""
    if not CACHE_ENABLED:
        return

    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{key}.json"
    
    try:
        logger.info("[Cache] SAVE (file) for key: %s...", key[:10])
        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')
    except (TypeError, IOError) as e:
        logger.error("[Cache] Failed to write to file cache for key %s: %s", key, e)

# --- Main Decorator ---

def cache_result(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """
    A decorator for async functions that caches their results.
    It checks an in-memory session cache first, then a file-based cache.
    If no cached result is found, it runs the function, caches the result,
    and then returns it.
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not CACHE_ENABLED:
            return await func(*args, **kwargs)

        # Use the function's qualified name for uniqueness
        func_name = func.__qualname__
        key = _get_cache_key(func_name, *args, **kwargs)

        # 1. Check short-term (session) memory
        if key in SESSION_CACHE:
            logger.info("[Cache] HIT (session) for key: %s...", key[:10])
            return SESSION_CACHE[key]

        # 2. Check long-term (file) memory
        cached_data = _get_from_file_cache(key)
        if cached_data is not None:
            # Store in session cache for faster access next time
            SESSION_CACHE[key] = cached_data
            return cached_data

        # 3. If not in cache, run the function
        logger.info("[Cache] MISS for key: %s... Running function %s.", key[:10], func_name)
        result = await func(*args, **kwargs)

        # 4. Save the result to both caches
        if result is not None:
            SESSION_CACHE[key] = result
            _save_to_file_cache(key, result)

        return result

    return wrapper
