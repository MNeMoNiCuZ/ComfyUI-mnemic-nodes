from .nodes.download_image_from_url import DownloadImageFromURL
from .nodes.save_text_file import SaveTextFile
from .nodes.get_file_path import GetFilePath
from .nodes.groq_api_llm import GroqAPILLM
from .nodes.groq_api_vlm import GroqAPIVLM
from .nodes.groq_api_alm_transcribe import GroqAPIALMTranscribe
#from .nodes.groq_api_alm_translate import GroqAPIALMTranslate
from .nodes.tiktoken_tokenizer import TiktokenTokenizer
from .nodes.string_cleaning import StringCleaning
from .nodes.generate_negative_prompt import GenerateNegativePrompt
from .nodes.lora_tag_loader import LoraTagLoader
from .nodes.resolution_selector import ResolutionSelector


NODE_CLASS_MAPPINGS = { 
    "📁 Get File Path": GetFilePath,
    "💾 Save Text File With Path": SaveTextFile,
    "🖼️ Download Image from URL": DownloadImageFromURL,
    "✨💬 Groq LLM API": GroqAPILLM,
    "✨📷 Groq VLM API": GroqAPIVLM,
    "✨📝 Groq ALM API - Transcribe": GroqAPIALMTranscribe,
    #"✨🌐 Groq ALM API - Translate [EN only]": GroqAPIALMTranslate,
    "🔠 Tiktoken Tokenizer Info": TiktokenTokenizer,
    "🧹 String Cleaning": StringCleaning,
    "🏷️ LoRA Loader Prompt Tags": LoraTagLoader,
    "📐 Resolution Image Size Selector": ResolutionSelector,
    "⛔ Generate Negative Prompt": GenerateNegativePrompt,
}

print("\033[34mMNeMiC Nodes: \033[92mLoaded\033[0m")
