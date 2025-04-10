import os
import time
import json
import urllib.parse
import urllib.request
import asyncio
from tqdm import tqdm
from googletrans import Translator
from subtitle_generator.llm import chat_llm
from subtitle_generator.utils import normalize_language_code_for_google, normalize_language_code_for_api

def niutrans_translate(sentence, src='en', dest='zh', apikey=''):
    """
    使用牛传翻译接口进行基础翻译，内置指数退避策略。

    参数：
      - sentence: 待翻译文本
      - src_lan: 源语言代码
      - tgt_lan: 目标语言代码
      - apikey: 接口密钥（若为空则从环境变量中读取）

    返回：
      - 翻译后文本（字符串），失败则返回原文
    """
    tgt_lan= normalize_language_code_for_api(dest)
    src_lan= normalize_language_code_for_api(src)
    if not apikey:
        apikey = os.getenv('niutrans_access_key')
    if sentence.strip() == "":
        print("空字符串，返回空")
        return ""
    base_url = 'http://api.niutrans.com/NiuTransServer/translation?'
    data = {"from": src_lan, "to": tgt_lan, "apikey": apikey, "src_text": sentence}
    query_string = urllib.parse.urlencode(data)
    req_url = base_url + "&" + query_string
    
    max_attempts = 5
    attempts = 0
    wait_time = 1
    while attempts < max_attempts:
        try:
            res = urllib.request.urlopen(req_url)
            res_content = res.read()
            res_dict = json.loads(res_content)
            if "tgt_text" in res_dict:
                return res_dict['tgt_text']
            else:
                attempts += 1
                print(f"翻译请求失败（尝试 {attempts}/{max_attempts}）：{res_dict}")
                time.sleep(wait_time)
                wait_time *= 2
        except Exception as e:
            attempts += 1
            print(f"翻译异常（尝试 {attempts}/{max_attempts}）：{e}")
            time.sleep(wait_time)
            wait_time *= 2
    return sentence

async def async_basic_translate(text, dest='zh-cn', src=None):
    """
    利用 googletrans 异步接口进行翻译，内置重试机制。

    参数：
      - text: 待翻译文本
      - dest: 目标语言（例如 "en"、"zh-cn"、"es" 等）
      - src: 源语言（若为空则自动检测）

    返回：
      - 翻译后文本（字符串），失败则返回原文
    """
    dest = normalize_language_code_for_google(dest)
    src = normalize_language_code_for_google(src) if src else None
    max_attempts = 10
    attempt = 0
    while attempt < max_attempts:
        try:
            async with Translator() as translator:
                if not src:
                    detection = await translator.detect(text)
                    print(f"检测到语言: {detection.lang} (置信度: {detection.confidence})")
                    src = detection.lang
                result = await translator.translate(text, src=src, dest=dest)
                return result.text
        except Exception as e:
            attempt += 1
            print(f"异步翻译尝试 {attempt} 次失败: {e}")
            await asyncio.sleep(1)
    print("所有异步翻译尝试失败，返回原文")
    return text

import asyncio
import time
from tqdm import tqdm  # 进度条模块

async def basic_translate_segments(segments, detected_language, translate_func, dest_language, concurrency_limit=5):
    """
    对所有段落使用基础翻译函数进行翻译。
    如果 translate_func 为异步函数，利用 asyncio 并发控制加速翻译并显示进度条；
    如果为同步函数，则在翻译过程中显示 tqdm 进度条，并进行重试。
    
    参数：
      - segments: 包含 "text" 键的段列表
      - detected_language: 源语言代码
      - translate_func: 翻译函数（如 niutrans_translate 或 async_basic_translate）
      - dest_language: 目标语言代码（例如 "en", "zh-cn", "es"）
      - concurrency_limit: 并发限制（仅对异步函数有效）
    
    返回：
      - 翻译结果列表，与 segments 顺序对应
    """
    basic_translations = []
    
    # 异步函数处理部分
    if asyncio.iscoroutinefunction(translate_func):
        semaphore = asyncio.Semaphore(concurrency_limit)
        max_attempts = 5
        delay = 1

        async def sem_translate(text):
            attempt = 0
            async with semaphore:
                while attempt < max_attempts:
                    try:
                        return await translate_func(text, src=detected_language, dest=dest_language)
                    except Exception as e:
                        attempt += 1
                        print(f"异步翻译尝试 {attempt}/{max_attempts} 失败: {e}")
                        await asyncio.sleep(delay * (2 ** (attempt - 1)))
                # 如果全部重试失败，则返回原文本
                return text

        # 使用进度条包装每个任务，保证任务结束时更新进度条且结果顺序不变
        progress_bar = tqdm(total=len(segments), desc="异步翻译中")
        async def task_wrapper(text):
            result = await sem_translate(text)
            progress_bar.update(1)
            return result
        
        tasks = [task_wrapper(seg["text"]) for seg in segments]
        basic_translations = await asyncio.gather(*tasks, return_exceptions=False)
        progress_bar.close()
        
    else:
        # 同步函数部分：带重试和 tqdm 进度条
        max_attempts = 5
        for seg in tqdm(segments, desc="基础翻译中"):
            original = seg["text"]
            attempts = 0
            while attempts < max_attempts:
                try:
                    basic_trans = translate_func(original, src=detected_language, dest=dest_language)
                    if isinstance(basic_trans, bytes):
                        basic_trans = basic_trans.decode('utf-8')
                    break
                except Exception as e:
                    attempts += 1
                    print(f"同步翻译调用失败（尝试 {attempts}/{max_attempts}）：{e}")
                    if attempts < max_attempts:
                        time.sleep(1)
                    else:
                        basic_trans = original
            basic_translations.append(str(basic_trans))
    return basic_translations

# 示例调用（需要根据具体环境定义 translate_func）
if __name__ == '__main__':
    import random

    # 示例：一个模拟的异步翻译函数，每次调用随机“失败”或返回翻译结果
    async def fake_async_translate(text, src, dest):
        await asyncio.sleep(0.1)  # 模拟网络延迟
        if random.random() < 0.2:
            raise Exception("翻译服务故障")
        return f"[{dest}] {text}"

    # 构造测试段落
    segments = [{"text": f"段落{i}内容"} for i in range(10)]
    detected_language = "zh-cn"
    dest_language = "en"

    # 使用异步翻译示例
    async def run_test():
        translations = await basic_translate_segments(segments, detected_language, fake_async_translate, dest_language)
        for original, trans in zip(segments, translations):
            print(f"原文: {original['text']} -> 翻译: {trans}")
    
    asyncio.run(run_test())


# async def basic_translate_segments(segments, detected_language, translate_func, dest_language, concurrency_limit=5):
#     """
#     对所有段落使用基础翻译函数进行翻译。
#     如果 translate_func 为异步函数，利用 asyncio 并发控制加速翻译；
#     如果为同步函数，则在翻译过程中显示 tqdm 进度条，并进行重试。
    
#     参数：
#       - segments: 包含 "text" 键的段列表
#       - detected_language: 源语言代码
#       - translate_func: 翻译函数（如 niutrans_translate 或 async_basic_translate）
#       - dest_language: 目标语言代码（例如 "en", "zh-cn", "es"）
#       - concurrency_limit: 并发限制（仅对异步函数有效）
    
#     返回：
#       - 翻译结果列表，与 segments 顺序对应
#     """
#     basic_translations = []
    
#     # 如果 translate_func 是异步函数，则用并发+重试策略
#     if asyncio.iscoroutinefunction(translate_func):
#         semaphore = asyncio.Semaphore(concurrency_limit)
#         async def sem_translate(text):
#             max_attempts = 5
#             delay = 1
#             async with semaphore:
#                 attempt = 0
#                 while attempt < max_attempts:
#                     try:
#                         return await translate_func(text, src=detected_language, dest=dest_language)
#                     except Exception as e:
#                         attempt += 1
#                         print(f"异步翻译尝试 {attempt}/{max_attempts} 失败: {e}")
#                         await asyncio.sleep(delay * (2 ** (attempt - 1)))
#                 # 如果全部重试失败，则返回原文本
#                 return text
#         tasks = [sem_translate(seg["text"]) for seg in segments]
#         basic_translations = await asyncio.gather(*tasks, return_exceptions=False)
#     else:
#         # 同步函数部分：原有代码，带重试和进度条
#         max_attempts = 5
#         for seg in tqdm(segments, desc="基础翻译中"):
#             original = seg["text"]
#             attempts = 0
#             while attempts < max_attempts:
#                 try:
#                     basic_trans = translate_func(original, src=detected_language, dest=dest_language)
#                     if isinstance(basic_trans, bytes):
#                         basic_trans = basic_trans.decode('utf-8')
#                     break
#                 except Exception as e:
#                     attempts += 1
#                     print(f"同步翻译调用失败（尝试 {attempts}/{max_attempts}）：{e}")
#                     if attempts < max_attempts:
#                         time.sleep(1)
#                     else:
#                         basic_trans = original
#             basic_translations.append(str(basic_trans))
#     return basic_translations



def select_best_translation(context_text, original, basic_translation, optimized_translation, api_key, dest_language, model_name=None, backend=None, logger=None):
    """
    利用 LLM 比较并选择最佳翻译结果。

    参数：
      - context_text: 上下文文本
      - original: 原文
      - basic_translation: 基础翻译结果
      - optimized_translation: 优化翻译结果
      - api_key: OpenAI API Key
      - dest_language: 目标语言代码（用于在 prompt 中说明翻译要求）
      - use_ollama: 是否使用 Ollama 接口
      - logger: 日志记录器，可选

    返回：
      - 最佳翻译文本（字符串）
    """
    prompt = f"""
你是一位翻译专家，请根据上下文推断当前场景，
比较以下两种将原文翻译成目标语言 ({dest_language}) 的翻译结果，并选择更符合原文与上下文的版本：
【上下文】：
{context_text}

【原文】：
{original}

【翻译0】：
{basic_translation}

【翻译1】：
{optimized_translation}

如果翻译0更好，返回数字 0；如果翻译1更好，返回数字 1。
仅返回一个数字。
"""
    response = chat_llm(prompt=prompt, sysprompt="You are a transcription evaluation expert.",model_name=model_name if model_name else None, api_key=api_key, backend=backend if backend else None, logger=logger)
    try:
        choice = int(response.strip())
        return basic_translation if choice == 0 else optimized_translation
    except ValueError:
        if logger:
            logger.warning(f"LLM 返回非数字响应: {response}，默认返回基础翻译")
        return basic_translation

def optimize_translation(original, basic_translation, context_text, api_key, dest_language, model_name=None, backend=None, logger=None):
    """
    利用 LLM 对基础翻译进行优化，使翻译更自然准确。

    参数：
      - original: 原文
      - basic_translation: 基础翻译结果
      - context_text: 上下文信息
      - openai_api_key: OpenAI API Key
      - dest_language: 目标语言代码，用于在 prompt 中说明应翻译成该语言
      - use_ollama: 是否使用 Ollama 接口
      - logger: 日志记录器，可选

    返回：
      - 优化后的翻译文本
    """
    # prompt = (
    #     f"You are an expert translator. Your task is to produce an accurate and natural translation of the original text into {dest_language}. "
    #     "Use the provided context only for clarification. Do not add or omit content.\n\n"
    #     f"【Original】: {original}\n"
    #     f"【Context】: {context_text}\n"
    #     f"【Basic Translation】: {basic_translation}\n\n"
    #     "Output only the optimized translation."
    # )

    # prompt = (
    #     "You are an expert translator. Your task is to provide the most accurate and natural Chinese translation of the given original text. "
    #     "The provided basic translation and context information are only for reference to ensure consistency in proper nouns, technical terms, and style. "
    #     "However, your translation must strictly reflect the meaning of the original text and must not be altered by the contextual information. "
    #     "Do not add, omit, or modify any content beyond what is present in the original text. Your goal is to produce the best possible translation based solely on the original text. "
    #     "【Original】: " + original + "\n"
    #     "【Basic Translation】(for reference only): " + basic_translation + "\n"
    #     "【Context】(for reference only): " + context_text + "\n"
    #     "Output only the translated Chinese text of the Original without any further explanations.\n\n"
    # )

    prompt = (
        f"You are an expert translator. Your task is to provide an accurate and natural \"{dest_language} language\" translation of the given original text. "
        "Use the provided context to help understand the meaning of the original text, especially if there are ambiguities. "
        "Do not add any information that is not present in the original text. Ensure that the translation is faithful to the original meaning. "
        "Maintain consistency in proper nouns and technical terms. The basic translation is provided for reference but should not limit your translation.\n\n"
        "Here are some examples to guide you:\n"
        "Example 1:\n"
        "Original: The bank is closed today.\n"
        "Context: 前文: We walked by the river yesterday. 后文: So we’ll have to withdraw money tomorrow.\n"
        "Accurate Translation: 银行今天关门了。\n"
        "(Reason: 'bank' refers to a financial institution, not a river bank, as clarified by the context.)\n\n"
        "Example 2:\n"
        "Original: She left the room in a hurry.\n"
        "Context: 前文: The meeting is about to start. 后文: Because she forgot her files.\n"
        "Accurate Translation: 她匆忙离开了房间。\n"
        "(Reason: The context confirms that she left quickly due to the meeting and forgotten files.)\n\n"
        "Example 3:\n"
        "Original: I need to charge my phone.\n"
        "Context: 前文: The battery is almost dead. 后文: Otherwise, I can’t contact you.\n"
        "Accurate Translation: 我得给手机充个电。\n"
        "(Reason: The context emphasizes the urgency, so a natural, colloquial translation is appropriate.)\n\n"
        "Example 4:\n"
        "Original: He’s working on a project.\n"
        "Context: 前文: He’s been busy lately. 后文: This project is very important.\n"
        "Accurate Translation: 他正在做一个项目。\n"
        "(Reason: The context confirms the basic translation is accurate.)\n\n"
        "Example 5:\n"
        "Original: We watched Avatar last night.\n"
        "Context: 前文: My friend recommended a movie. 后文: The effects were amazing.\n"
        "Accurate Translation: 我们昨晚看了《阿凡达》。\n"
        "(Reason: 'Avatar' is a proper noun for a movie, so it should be translated accordingly.)\n\n"
        "Now, provide an accurate \"{dest_language} language\" translation for the following original text:\n"
        "【Original】: " + original + "\n"
        "【Context】: " + context_text + "\n"
        "【Basic Translation (for reference)】: " + basic_translation + "\n"
       f"Output only the accurate \"{dest_language} language\" translation of the Original. Do not include any additional explanations or content."
    )

    optimized_translation = chat_llm(prompt=prompt, sysprompt="You are a transcription optimization expert.",model_name=model_name if model_name else None, api_key=api_key, backend=backend if backend else None, logger=logger)
    return optimized_translation if optimized_translation else basic_translation

from tqdm import tqdm

def optimize_translations_with_context(segments, basic_translations,
                                       use_llm=True, context_range=10, api_key=None, dest_language="zh", model_name=None, backend=None, logger=None):
    """
    针对每个段落利用上下文信息进一步优化翻译结果。

    参数：
      - segments: 段列表（包含 "start", "end", "text"）
      - basic_translations: 对应的基础翻译结果列表
      - optimize_translation_func: 优化翻译函数接口
      - use_llm: 是否启用 LLM 优化
      - context_range: 上下文段数
      - api_key: OpenAI API Key
      - dest_language: 目标语言代码
      - use_ollama: 是否使用 Ollama 接口
      - logger: 日志记录器，可选

    返回：
      - 包含优化翻译的段列表（字典列表）
    """
    final_segments = []
    # 使用 tqdm 显示进度条
    for i in tqdm(range(len(segments)), desc="优化翻译中"):
        seg = segments[i]
        original = seg["text"]
        basic_trans = basic_translations[i]
        context_parts = []
        if i > 0:
            start_idx = max(0, i - context_range)
            context_parts.append("前文: " + "\n".join(basic_translations[start_idx:i]))
        if i < len(segments) - 1:
            end_idx = min(len(segments), i + context_range + 1)
            context_parts.append("后文: " + "\n".join(basic_translations[i+1:end_idx]))
        context_text = "\n".join(context_parts)
        if use_llm:
            optimized_trans = optimize_translation(original, basic_trans, context_text, api_key, dest_language, model_name=model_name if model_name else None, backend=backend if backend else None, logger=logger)
            if not basic_trans==optimized_trans:
                optimized_trans = select_best_translation(context_text, original, basic_trans, optimized_trans, api_key, dest_language, model_name=model_name if model_name else None, backend=backend if backend else None, logger=logger)
            basic_translations[i] = optimized_trans
        else:
            optimized_trans = basic_trans
        final_segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": optimized_trans,
            "speaker": seg.get("speaker", "")
        })
    return final_segments
