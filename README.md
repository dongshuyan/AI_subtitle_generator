# AI Subtitle Generator

AI Subtitle Generator 是一个集成转录、分段、翻译和 LLM 优化等技术的强大视频字幕生成工具。
它合并了 Whisper 语音转录、Ollama / OpenAI GPT 类的 LLM 模型和多种翻译接口，可以将任意视频自动生成多语言字幕，是对视频内容进行分析、翻译和调优的最优解决方案之一。

功能特色:
- 【视频处理】 支持任意格式的视频，自动抽取音频，并处理后继续转录。
- 【语音转录】 基于 Whisper 模型，支持自动语言检测，培金后转录，且支持指定语言。
- 【段落处理】 支持基于 LLM 的转录精精补充、合并断句，使字幕更精精。
- 【翻译模块】 支持基础翻译（GoogleTrans、Niutrans），配合 LLM 算法进行上下文优化处理，翻译效果优质，支持多国语言转换。
- 【字幕生成】 支持 SRT 和 ASS 格式，自动合并重复段落，管理多说话者。
- 【安全、缓处理】 完善的异常处理和重试策略，确保程序结束后自动删除临时文件。

---

## Setup

### 1. 配置 Spleeter
```bash
conda create -n spleeter python=3.8
conda activate spleeter
conda install -c conda-forge ffmpeg libsndfile
pip install spleeter
```
同时，需要手动下载预训练模型：

- 下载地址： https://github.com/deezer/spleeter/releases/download/v1.4.0/2stems.tar.gz
- 解压后目录结构：
```
spleeter/
├── pretrained_models
│   └── 2stems
│       ├── checkpoint
│       ├── model.data-00000-of-00001
│       ├── model.index
│       └── model.meta
```
然后根据自己环境的具体情况配置环境变量，例如：
```bash
export SPLEETER_PATH="/Tools/Spleeter"
export CONDA_BASE_PATH="/opt/miniconda3"
```
更多详细可参考：https://github.com/deezer/spleeter

### 2. 配置 subtitle_generator
```bash
conda create -n subtitle python=3.11
conda activate subtitle
pip install -r requirements.txt
```

### 3. 环境变量
请确保已配置以下环境变量：
- `SPLEETER_PATH` : Spleeter模型文件根目录
- `CONDA_BASE_PATH`: Conda/Miniconda安装根目录
- `niutrans_access_key`: 小牛翻译 APIKey (申请: https://niutrans.com/)
- `OPENAI_API_KEY`: OpenAI API Key (申请: https://platform.openai.com/)
- `Whisper_model_path`: Whisper本地模型文件目录

---

## Python usage

支持参数：
- `--video`: 必选，视频文件路径
- `--target_lang`: 目标字幕语言（默认 zh）
- `--openai_key`: OpenAI API Key（不指定则使用环境变量）
- `--llm_backend`: LLM 接口类型，支持 "gpt" | "ollama" (默认: gpt)
- `--model_name`: LLM 模型名，如 gpt-4o、huihui_ai/qwen2.5-1m
- `--notuse_spleeter`: 不使用 spleeter 进行音频分离
- `--use_llm_correction`: 使用 LLM 进行转录精精修正
- `--use_llm_segmentation`: 使用 LLM 进行断句合并处理
- `--use_llm_translation`: 使用 LLM 进行翻译优化
- `--model_size`: Whisper 模型大小，如 base, medium, large-v3 (默认为 config.py 设置)
- `--source_lang`: 指定转录语言（空则自动检测）
- `--log`: 记录 LLM 作用日志

无论是研究视频 AI 分析或者生产实操需求，AI Subtitle Generator 均是性能丰富且易于扩展的选择。

示例命令
```bash
cd src
python -m subtitle_generator.cli --video '~/Downloads/test.mkv' --target_lang zh --use_llm_correction --use_llm_segmentation --use_llm_translation --log --llm_backend 'gpt' --model_name 'gpt-4o'
```