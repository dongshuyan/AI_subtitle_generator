"""
配置文件，定义系统中使用的全局默认参数。
"""

# 默认 Whisper 模型大小（可通过命令行参数覆盖）
DEFAULT_WHISPER_MODEL = "large-v3"

# 默认翻译目标语言（如果用户未指定则默认翻译成中文）
DEFAULT_TARGET_LANGUAGE = "zh"

# 默认 LLM 模型名称（如使用 Ollama 时的模型标识）
DEFAULT_LLM_MODEL = "huihui_ai/qwen2.5-1m-abliterated:7b"
