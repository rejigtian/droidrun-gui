import importlib
import logging
from typing import Any
from llama_index.core.llms.llm import LLM
# Configure logging
logger = logging.getLogger("droidrun")

def load_llm(provider_name: str, **kwargs: Any) -> LLM:
    """
    Dynamically loads and initializes a LlamaIndex LLM.

    Imports `llama_index.llms.<provider_name_lower>`, finds the class named
    `provider_name` within that module, verifies it's an LLM subclass,
    and initializes it with kwargs.

    Args:
        provider_name: The case-sensitive name of the provider and the class
                       (e.g., "OpenAI", "Ollama", "HuggingFaceLLM").
        **kwargs: Keyword arguments for the LLM class constructor.

    Returns:
        An initialized LLM instance.

    Raises:
        ModuleNotFoundError: If the provider's module cannot be found.
        AttributeError: If the class `provider_name` is not found in the module.
        TypeError: If the found class is not a subclass of LLM or if kwargs are invalid.
        RuntimeError: For other initialization errors.
    """
    if not provider_name:
        raise ValueError("provider_name cannot be empty.")
    if provider_name == "OpenAILike":
        module_provider_part = "openai_like"
        kwargs.setdefault("is_chat_model", True)
    elif provider_name == "GoogleGenAI":
        module_provider_part = "google_genai"
    else:
        # Use lowercase for module path, handle hyphens for package name suggestion
        lower_provider_name = provider_name.lower()
        # Special case common variations like HuggingFaceLLM -> huggingface module
        if lower_provider_name.endswith("llm"):
            module_provider_part = lower_provider_name[:-3].replace("-", "_")
        else:
            module_provider_part = lower_provider_name.replace("-", "_")
    module_path = f"llama_index.llms.{module_provider_part}"
    install_package_name = f"llama-index-llms-{module_provider_part.replace('_', '-')}"

    try:
        logger.debug(f"Attempting to import module: {module_path}")
        llm_module = importlib.import_module(module_path)
        logger.debug(f"Successfully imported module: {module_path}")

    except ModuleNotFoundError:
        logger.error(f"Module '{module_path}' not found. Try: pip install {install_package_name}")
        raise ModuleNotFoundError(
            f"Could not import '{module_path}'. Is '{install_package_name}' installed?"
        ) from None

    try:
        logger.debug(f"Attempting to get class '{provider_name}' from module {module_path}")
        llm_class = getattr(llm_module, provider_name)
        logger.debug(f"Found class: {llm_class.__name__}")

        # Verify the class is a subclass of LLM
        if not isinstance(llm_class, type) or not issubclass(llm_class, LLM):
            raise TypeError(f"Class '{provider_name}' found in '{module_path}' is not a valid LLM subclass.")

        # Filter out None values from kwargs
        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        # Initialize
        logger.debug(f"Initializing {llm_class.__name__} with kwargs: {list(filtered_kwargs.keys())}")
        llm_instance = llm_class(**filtered_kwargs)
        logger.debug(f"Successfully loaded and initialized LLM: {provider_name}")
        if not llm_instance:
            raise RuntimeError(f"Failed to initialize LLM instance for {provider_name}.")
        return llm_instance

    except AttributeError:
        logger.error(f"Class '{provider_name}' not found in module '{module_path}'.")
        raise AttributeError(
            f"Could not find class '{provider_name}' in module '{module_path}'. Check spelling and capitalization."
        ) from None
    except TypeError as e:
        logger.error(f"Error initializing {provider_name}: {e}")
        raise # Re-raise TypeError (could be from issubclass check or __init__)
    except Exception as e:
        logger.error(f"An unexpected error occurred initializing {provider_name}: {e}")
        raise e
    
# --- Example Usage ---
if __name__ == "__main__":
    # Install the specific LLM integrations you want to test:
    # pip install \
    #   llama-index-llms-anthropic \
    #   llama-index-llms-deepseek \
    #   llama-index-llms-gemini \
    #   llama-index-llms-openai

    # Example 1: Load Anthropic (requires ANTHROPIC_API_KEY env var or kwarg)
    print("\n--- Loading Anthropic ---")
    try:
        anthropic_llm = load_llm(
            "Anthropic",
            model="claude-3-7-sonnet-latest",
        )
        print(f"Loaded LLM: {type(anthropic_llm)}")
        print(f"Model: {anthropic_llm.metadata}")
    except Exception as e:
        print(f"Failed to load Anthropic: {e}")

    # Example 2: Load DeepSeek (requires DEEPSEEK_API_KEY env var or kwarg)
    print("\n--- Loading DeepSeek ---")
    try:
        deepseek_llm = load_llm(
            "DeepSeek",
            model="deepseek-reasoner",
            api_key="your api",  # or set DEEPSEEK_API_KEY
        )
        print(f"Loaded LLM: {type(deepseek_llm)}")
        print(f"Model: {deepseek_llm.metadata}")
    except Exception as e:
        print(f"Failed to load DeepSeek: {e}")

    # Example 3: Load Gemini (requires GOOGLE_APPLICATION_CREDENTIALS or kwarg)
    print("\n--- Loading Gemini ---")
    try:
        gemini_llm = load_llm(
            "Gemini",
            model="gemini-2.0-fash",
        )
        print(f"Loaded LLM: {type(gemini_llm)}")
        print(f"Model: {gemini_llm.metadata}")
    except Exception as e:
        print(f"Failed to load Gemini: {e}")

    # Example 4: Load OpenAI (requires OPENAI_API_KEY env var or kwarg)
    print("\n--- Loading OpenAI ---")
    try:
        openai_llm = load_llm(
            "OpenAI",
            model="gp-4o",
            temperature=0.5,
        )
        print(f"Loaded LLM: {type(openai_llm)}")
        print(f"Model: {openai_llm.metadata}")
    except Exception as e:
        print(f"Failed to load OpenAI: {e}")
