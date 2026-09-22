from .utils.colorama import ensure_colorama_initialized
ensure_colorama_initialized()

from comfy_api.latest import ComfyAPI, ComfyExtension, io

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
from .nodes.ideogram4_prompt_builder import Ideogram4PromptBuilder
from .nodes.ideogram4_random_prompter import Ideogram4RandomPrompter
from .nodes.image_save_with_metadata import ImageSaveWithMetadata
from .utils.image_save_runtime_hook import install_runtime_hooks


_api = ComfyAPI()

# Node ids used to be the emoji display strings. They are now ASCII
# (MNeMiC_*), and every old id is mapped to its new node here so workflows
# saved before the rename keep loading. Never remove an entry from this map.
LEGACY_NODE_IDS = {
    "📁 Get File Path": "MNeMiC_GetFilePath",
    "💾 Save Text File With Path": "MNeMiC_SaveTextFile",
    "🖼️ Download Image from URL": "MNeMiC_DownloadImageFromURL",
    "✨💬 Groq LLM API": "MNeMiC_GroqAPILLM",
    "✨📷 Groq VLM API": "MNeMiC_GroqAPIVLM",
    "✨📝 Groq ALM API - Transcribe": "MNeMiC_GroqAPIALMTranscribe",
    "✨🌐 Groq ALM API - Translate [EN only]": "MNeMiC_GroqAPIALMTranslate",
    "🔠 Tiktoken Tokenizer Info": "MNeMiC_TiktokenTokenizer",
    "🧹 String Cleaning": "MNeMiC_StringCleaning",
    "🏷️ LoRA Loader Prompt Tags": "MNeMiC_LoraTagLoader",
    "📐 Resolution Image Size Selector": "MNeMiC_ResolutionSelector",
    "📝 Wildcard Processor": "MNeMiC_WildcardProcessor",
    "📝 Wildcard Processor Advanced": "MNeMiC_WildcardProcessorAdvanced",
    "🔀 Batch Wildcard Upscale Sampler": "MNeMiC_BatchWildcardSampler",
    "⚙️ Prompt Property Extractor": "MNeMiC_PromptPropertyExtractor",
    "⛔ Generate Negative Prompt": "MNeMiC_GenerateNegativePrompt",
    "✂️ String Text Splitter": "MNeMiC_StringTextSplitter",
    "✂️ String Text Extractor": "MNeMiC_StringTextExtractor",
    "📅 Format Date Time": "MNeMiC_FormatDateTime",
    "🖼️📊 Metadata Extractor (Single)": "MNeMiC_MetadataExtractorSingle",
    "🖼️📊 Metadata Extractor (List)": "MNeMiC_MetadataExtractorList",
    "🖼️+📝 Load Text-Image Pair (Single)": "MNeMiC_LoadTextImagePairSingle",
    "🖼️+📝 Load Text-Image Pairs (List)": "MNeMiC_LoadTextImagePairsList",
    "🎵📊 Audio Visualizer": "MNeMiC_AudioVisualizer",
    "🖼️ Load Image Advanced": "MNeMiC_LoadImageAdvanced",
    "🎨 Colorful Starting Image": "MNeMiC_ColorfulStartingImage",
    "🎲 Load Random Checkpoint": "MNeMiC_LoadRandomCheckpoint",
    "📂 Load Images From Path": "MNeMiC_LoadImagesFromPath",
    "🎲 Random Int in Range": "MNeMiC_RandomIntInRange",
    "🎲 Random Float in Range": "MNeMiC_RandomFloatInRange",
    "🎲 Random Bool": "MNeMiC_RandomBool",
    "🎲 Random String": "MNeMiC_RandomString",
    "🎲 Random Seed": "MNeMiC_RandomSeed",
    "🎲 Random Color": "MNeMiC_RandomColor",
    "🔗 String Concat / Append": "MNeMiC_StringConcat",
    "✏️ Literal Bool": "MNeMiC_LiteralBool",
    "✏️ Literal Int": "MNeMiC_LiteralInt",
    "✏️ Literal Float": "MNeMiC_LiteralFloat",
    "✏️ Literal String": "MNeMiC_LiteralString",
    "🖼️ Load Image Temporarily": "MNeMiC_LoadImageTemporarily",
    "🧩 Ideogram 4 Prompt Builder w. String Inputs": "MNeMiC_Ideogram4PromptBuilder",
    "🎲 Ideogram 4 Random Prompter": "MNeMiC_Ideogram4RandomPrompter",
    "💾 Save Image With Metadata": "MNeMiC_ImageSaveWithMetadata",
}


def _has_control_after_generate(node_input, input_id: str) -> bool:
    """Whether the frontend gives this widget a linked control-after-generate.

    It does so when the input asks for one, and automatically for any INT
    widget named `seed` or `noise_seed`.
    """
    declared = getattr(node_input, "control_after_generate", None)
    if declared is not None:
        return bool(declared)
    return isinstance(node_input, io.Int.Input) and input_id in ("seed", "noise_seed")


def _build_replacement(old_node_id: str, node_cls: type[io.ComfyNode]) -> io.NodeReplace:
    """Describe an id-only rename to ComfyUI's node replacement system.

    Inputs and outputs are unchanged, so everything maps to itself — but both
    mappings still have to be spelled out. The replacement builds a brand new
    node and then moves connections across one entry at a time: an input that
    is not listed loses its link and its widget value, and an output that is
    not listed loses every link leaving it. A `None` mapping is not "keep as
    is", it means "carry nothing".

    `old_widget_ids` gives the widget order, which is how positional widget
    values in a saved workflow JSON are matched back to input ids.
    """
    schema = node_cls.GET_SCHEMA()
    input_ids = []
    widget_ids = []
    for node_input in schema.inputs:
        input_id = getattr(node_input, "id", None)
        if input_id is None:
            continue
        input_ids.append(input_id)
        is_widget = isinstance(node_input, io.WidgetInput) and not getattr(node_input, "force_input", False)
        if not is_widget:
            continue  # sockets are not in widgets_values
        widget_ids.append(input_id)
        if _has_control_after_generate(node_input, input_id):
            # The frontend attaches a linked "control after generate" widget to
            # these, and it takes its own slot in the saved widgets_values
            # array. old_widget_ids is matched against that array by position,
            # so the slot has to be accounted for or every widget after the
            # seed is read one place early. The placeholder is never used as a
            # mapping id, so the new node's own control widget keeps its
            # default.
            widget_ids.append(f"{input_id}_control_after_generate")
    return io.NodeReplace(
        new_node_id=schema.node_id,
        old_node_id=old_node_id,
        old_widget_ids=widget_ids,
        input_mapping=[{"new_id": i, "old_id": i} for i in input_ids],
        output_mapping=[{"new_idx": i, "old_idx": i} for i in range(len(schema.outputs))],
    )


class MnemicExtension(ComfyExtension):
    async def on_load(self) -> None:
        install_runtime_hooks("ImageSaveWithMetadata")

        by_new_id = {}
        for node_cls in await self.get_node_list():
            by_new_id[node_cls.GET_SCHEMA().node_id] = node_cls
        for old_node_id, new_node_id in LEGACY_NODE_IDS.items():
            node_cls = by_new_id.get(new_node_id)
            if node_cls is None:
                continue  # node is not currently registered; nothing to migrate to
            await _api.node_replacement.register(_build_replacement(old_node_id, node_cls))

    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            GetFilePath,
            SaveTextFile,
            DownloadImageFromURL,
            GroqAPILLM,
            GroqAPIVLM,
            GroqAPIALMTranscribe,
            #GroqAPIALMTranslate,
            TiktokenTokenizer,
            StringCleaning,
            LoraTagLoader,
            ResolutionSelector,
            WildcardProcessor,
            WildcardProcessorAdvanced,
            BatchWildcardSampler,
            PromptPropertyExtractor,
            GenerateNegativePrompt,
            StringTextSplitter,
            StringTextExtractor,
            FormatDateTime,
            MetadataExtractorSingle,
            MetadataExtractorList,
            LoadTextImagePairSingle,
            LoadTextImagePairsList,
            AudioVisualizer,
            LoadImageAdvanced,
            ColorfulStartingImage,
            LoadRandomCheckpoint,
            LoadImagesFromPath,
            RandomIntInRange,
            RandomFloatInRange,
            RandomBool,
            RandomString,
            RandomSeed,
            RandomColor,
            StringConcat,
            LiteralBool,
            LiteralInt,
            LiteralFloat,
            LiteralString,
            LoadImageTemporarily,
            Ideogram4PromptBuilder,
            Ideogram4RandomPrompter,
            ImageSaveWithMetadata,
        ]


async def comfy_entrypoint() -> MnemicExtension:
    return MnemicExtension()


WEB_DIRECTORY = "./web"
__all__ = ["comfy_entrypoint", "WEB_DIRECTORY"]

print("\033[34m⚡ MNeMiC Nodes: \033[92mLoaded\033[0m")
