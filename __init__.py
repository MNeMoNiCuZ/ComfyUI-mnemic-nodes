from .utils.colorama import ensure_colorama_initialized
ensure_colorama_initialized()

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
from .nodes.wildcard_processor import WildcardProcessor
from .nodes.wildcard_processor_advanced import WildcardProcessor as WildcardProcessorAdvanced
from .nodes.batch_wildcard_sampler import BatchWildcardSampler
from .nodes.string_text_splitter import StringTextSplitter
from .nodes.string_text_extractor import StringTextExtractor
from .nodes.format_date_time import FormatDateTime
from .nodes.load_text_image_pair_single import LoadTextImagePairSingle
from .nodes.load_text_image_pairs_list import LoadTextImagePairsList
from .nodes.metadata_extractor_single import MetadataExtractorSingle
from .nodes.metadata_extractor_list import MetadataExtractorList
from .nodes.audio_visualizer import AudioVisualizer
from .nodes.load_image_advanced import LoadImageAdvanced
from .nodes.prompt_property_extractor import PromptPropertyExtractor

from .nodes.colorful_starting_image import ColorfulStartingImage
from .nodes.load_random_checkpoint import LoadRandomCheckpoint
from .nodes.load_images import LoadImagesFromPath
from .nodes.random_int_in_range import RandomIntInRange
from .nodes.random_float_in_range import RandomFloatInRange
from .nodes.random_bool import RandomBool
from .nodes.random_string import RandomString
from .nodes.random_seed import RandomSeed
from .nodes.random_color import RandomColor
from .nodes.string_concat import StringConcat
from .nodes.literal_bool import LiteralBool
from .nodes.literal_int import LiteralInt
from .nodes.literal_float import LiteralFloat
from .nodes.literal_string import LiteralString
from .nodes.load_image_temporarily import LoadImageTemporarily
from .nodes.image_save_with_metadata import ImageSaveWithMetadata
from .utils.image_save_runtime_hook import install_runtime_hooks

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
    "📝 Wildcard Processor": WildcardProcessor,
    "📝 Wildcard Processor Advanced": WildcardProcessorAdvanced,
    "🔀 Batch Wildcard Sampler": BatchWildcardSampler,
    "⚙️ Prompt Property Extractor": PromptPropertyExtractor,
    "⛔ Generate Negative Prompt": GenerateNegativePrompt,
    "✂️ String Text Splitter": StringTextSplitter,
    "✂️ String Text Extractor": StringTextExtractor,
    "📅 Format Date Time": FormatDateTime,
    "🖼️📊 Metadata Extractor (Single)": MetadataExtractorSingle,
    "🖼️📊 Metadata Extractor (List)": MetadataExtractorList,
    "🖼️+📝 Load Text-Image Pair (Single)": LoadTextImagePairSingle,
    "🖼️+📝 Load Text-Image Pairs (List)": LoadTextImagePairsList,
    "🎵📊 Audio Visualizer": AudioVisualizer,
    "🖼️ Load Image Advanced": LoadImageAdvanced,
    "🎨 Colorful Starting Image": ColorfulStartingImage,
    "🎲 Load Random Checkpoint": LoadRandomCheckpoint,
    "📂 Load Images From Path": LoadImagesFromPath,
    "🎲 Random Int in Range": RandomIntInRange,
    "🎲 Random Float in Range": RandomFloatInRange,
    "🎲 Random Bool": RandomBool,
    "🎲 Random String": RandomString,
    "🎲 Random Seed": RandomSeed,
    "🎲 Random Color": RandomColor,
    "🔗 String Concat / Append": StringConcat,
    "✏️ Literal Bool": LiteralBool,
    "✏️ Literal Int": LiteralInt,
    "✏️ Literal Float": LiteralFloat,
    "✏️ Literal String": LiteralString,
    "🖼️ Load Image Temporarily": LoadImageTemporarily,
    "💾 Save Image With Metadata": ImageSaveWithMetadata,
}

NODE_DISPLAY_NAME_MAPPINGS = {}

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
install_runtime_hooks("ImageSaveWithMetadata")

print("\033[34m⚡ MNeMiC Nodes: \033[92mLoaded\033[0m")
