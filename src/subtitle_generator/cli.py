import os
import argparse
import asyncio
from subtitle_generator import config
from subtitle_generator.logging import setup_logger
from subtitle_generator.video_processing import extract_audio_from_video
from subtitle_generator.transcription import transcribe_audio_whisper, post_process_segments
from subtitle_generator.segmentation import llm_correct_segments, llm_merge_segments
from subtitle_generator.translation import (
    basic_translate_segments, async_basic_translate, niutrans_translate,
    optimize_translations_with_context, optimize_translation, normalize_language_code_for_api
)
from subtitle_generator.subtitles import generate_srt, generate_ass
from subtitle_generator.utils import safe_remove, copy_video_to_temp, delete_temp_folder

def parse_args():
    parser = argparse.ArgumentParser(description="视频字幕生成工具（基于 Whisper、LLM 与翻译优化）")
    parser.add_argument("--video", required=True, help="输入视频文件路径")
    parser.add_argument("--openai_key", default="", help="OpenAI API Key（用于 LLM 模块）")
    parser.add_argument("--target_lang", default=config.DEFAULT_TARGET_LANGUAGE, help="目标字幕语言（例如 zh, en, es 等）")
    # 新增统一控制 LLM 后端的参数，取值 "gpt" 或 "ollama"，未来可扩展更多
    parser.add_argument("--llm_backend", default="gpt", help="LLM 后端接口类型（例如 'gpt' 或 'ollama'）")
    parser.add_argument("--model_name", default=None, help="用于 LLM 模块的模型名称（例如 'gpt-4o' 或 Ollama 模型名称），默认为各后端默认值")
    parser.add_argument("--notuse_spleeter", action="store_true", help="不使用 spleeter 进行音频分离")
    parser.add_argument("--use_llm_correction", action="store_true", help="是否使用 LLM 进行转录纠错")
    parser.add_argument("--use_llm_segmentation", action="store_true", help="是否使用 LLM 进行断句合并优化")
    parser.add_argument("--use_llm_translation", action="store_true", help="是否使用 LLM 进行翻译优化")
    parser.add_argument("--log", action="store_true", help="是否记录 LLM 日志")
    parser.add_argument("--model_size", default=config.DEFAULT_WHISPER_MODEL, help="Whisper 模型大小")
    parser.add_argument("--source_lang", default="", help="转录语言（空则自动检测）")
    return parser.parse_args()

async def main():
    args = parse_args()

    # 将目标语言标准化（这里适用于 API 的标准化规则）
    args.target_lang = normalize_language_code_for_api(args.target_lang)
    logger = setup_logger() if args.log else None

    try:
        api_key = args.openai_key or os.getenv("OPENAI_API_KEY")
        if args.llm_backend.lower() == "gpt" and not api_key:
            raise ValueError("当使用 GPT 作为 LLM 后端时，必须设置 OPENAI_API_KEY 环境变量或通过 --openai_key 参数提供。")
        
        # 保存原始视频路径，用于后续生成字幕文件命名
        original_video_path = args.video

        # 将视频复制到下载目录下的临时目录，并更新 args.video 为临时视频路径
        temp_video_path = copy_video_to_temp(original_video_path)
        args.video = temp_video_path  # e.g. ~/Downloads/subtitle_generator/test/test1.mp4

        # 将所有中间生成的文件都放在该临时目录中
        temp_dir = os.path.dirname(temp_video_path)
        temp_audio_path = os.path.join(temp_dir, "temp_audio.wav")
        
        # 1. 视频 → 音频提取
        extract_audio_from_video(args.video, temp_audio_path)
        
        # 2. 语音转录
        if args.source_lang:
            transcription_result = transcribe_audio_whisper(temp_audio_path, notuse_spleeter=args.notuse_spleeter, model_size=args.model_size, language=args.source_lang)
        else:
            transcription_result = transcribe_audio_whisper(temp_audio_path, notuse_spleeter=args.notuse_spleeter, model_size=args.model_size)
        raw_segments = transcription_result.get("segments", [])
        print(f"语音识别完成，共识别段数：{len(raw_segments)}")
        if logger:
            for i, seg in enumerate(raw_segments):
                logger.info(f"段 {i+1}: {seg['text']} (开始: {seg['start']}, 结束: {seg['end']})")
        
        processed_segments = post_process_segments(raw_segments)
        print(f"后处理完成，处理后段数：{len(processed_segments)}")
        if logger:
            logger.info(f"后处理完成，处理后段数：{len(processed_segments)}")
        
        # 生成原始字幕（文件名使用原始视频路径）
        video_basename = os.path.splitext(original_video_path)[0]
        detected_language = transcription_result.get("language", "en")
        srt_output = f"{video_basename}.{detected_language}.srt"
        ass_output = f"{video_basename}.{detected_language}.ass"
        generate_srt(processed_segments, srt_output)
        generate_ass(processed_segments, ass_output)
        print(f"原始字幕文件生成完成：{srt_output}")
        
        # 3. 可选 LLM 纠错
        if args.use_llm_correction:
            processed_segments = llm_correct_segments(processed_segments, api_key, model_name=args.model_name, backend=args.llm_backend, logger=logger)
            print("LLM 转录纠错完成。")
        else:
            print("未启用 LLM 转录纠错。")
        
        # 4. 可选 LLM 断句合并优化
        if args.use_llm_segmentation:
            processed_segments = llm_merge_segments(processed_segments, api_key, model_name=args.model_name, backend=args.llm_backend, logger=logger)
            print("LLM 断句合并优化完成。")
        else:
            print("未启用 LLM 断句优化。")
        
        # 5. 翻译（当目标语言与检测到的语言不一致时进行翻译）
        if args.target_lang.lower() not in detected_language.lower():
            # 根据所使用的翻译接口，这里示例中我们根据 llm_backend 选择使用异步方式（通常 googletrans 使用异步）
            if args.llm_backend.lower() == "ollama":
                basic_translations = await basic_translate_segments(processed_segments, detected_language, niutrans_translate, args.target_lang)
            else:
                basic_translations = await basic_translate_segments(processed_segments, detected_language, async_basic_translate, args.target_lang)

            print("基础翻译完成。")
            final_segments = optimize_translations_with_context(
                processed_segments,
                basic_translations,
                use_llm=args.use_llm_translation,
                context_range=10,
                api_key=api_key,
                dest_language=args.target_lang,
                model_name=args.model_name,
                backend=args.llm_backend,
                logger=logger
            )
            print("翻译及优化完成。")
        else:
            final_segments = processed_segments
            print("源语言与目标字幕语言一致，跳过翻译。")
        
        final_srt = f"{video_basename}.srt"
        final_ass = f"{video_basename}.ass"
        generate_srt(final_segments, final_srt)
        generate_ass(final_segments, final_ass)
        print(f"最终字幕文件生成完成：\nSRT：{final_srt}\nASS：{final_ass}")
        
    except Exception as e:
        print(f"程序异常终止：{e}")
        if logger:
            logger.error(f"程序异常终止：{e}")
    finally:
        # 删除临时音频文件
        safe_remove(temp_audio_path)
        # 删除复制视频所在的临时目录
        delete_temp_folder(args.video)

if __name__ == "__main__":
    asyncio.run(main())
