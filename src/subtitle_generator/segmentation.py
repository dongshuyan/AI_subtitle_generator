import time
from tqdm import tqdm
from subtitle_generator.llm import chat_llm


def llm_correct_segments(segments, api_key, context_range=10, model_name=None, backend=None, logger=None):
    """
    对每个转录段利用 LLM 进行纠错，参考前后 context_range 段上下文信息。
    如果某个 segment 的文本为空，则不进行纠错，直接保留。

    参数：
      - segments: 转录段列表（字典列表，每个包含 "text" 等键）
      - openai_api_key: OpenAI API Key（如不使用 Ollama 时必须提供）
      - context_range: 上下文段数
      - use_ollama: 是否使用 Ollama 接口
      - logger: 日志记录器，可选
    返回：
      - corrected_segments: 经过纠错的段列表
    """
    if not segments:
        return segments
    corrected_segments = []
    total = len(segments)
    for i, seg in enumerate(tqdm(segments, desc="LLM 纠错进度")):
        # 如果当前段的 text 为空，直接保留
        if not seg.get("text", "").strip():
            corrected_segments.append(seg)
            continue

        context = ""
        start_idx = max(0, i - context_range)
        previous_context = [segments[j]["text"] for j in range(start_idx, i) if segments[j].get("text", "").strip()]
        if previous_context:
            context += "Previous context: " + " ".join(previous_context) + "\n"
        end_idx = min(total, i + context_range + 1)
        next_context = [segments[j]["text"] for j in range(i + 1, end_idx) if segments[j].get("text", "").strip()]
        if next_context:
            context += "Next context: " + " ".join(next_context) + "\n"
        
        prompt = (
            "You are an expert in correcting transcription errors across multiple languages. \n"
            "Your task is to correct transcription errors in the given segment, using the provided context from surrounding segments. \n"
            "Errors may include misheard words, homophones, or other common transcription mistakes. \n"
            "Only correct errors that you are 100% certain about, and do not modify content that is not erroneous. \n"
            "Maintain the original language and do not change the language.\n\n"
            "Here are some examples to guide you:\n\n"
            "Example 1:\n"
            "Previous context: I've already run a kilometer.\n"
            "Current segment: I feel thirty.\n"
            "Corrected text: I feel thirsty.\n\n"
            "Example 2:\n"
            "Previous context: 昨日、おばあさんに会いました。\n"
            "Current segment: 彼女は私の obasan です。\n"
            "Corrected text: 彼女は私の おばさん です。\n\n"
            "Example 3:\n"
            "Previous context: 我昨天买了一匹马。\n"
            "Current segment: 我妈很喜欢它。\n"
            "Corrected text: 我妈很喜欢它。\n\n"
            "Example 4:\n"
            "Previous context: 我在学习日本語。\n"
            "Current segment: 我的 sensei はとても厳しいです。\n"
            "Corrected text: 我的 先生 はとても厳しいです。\n\n"
            "Example 5:\n"
            "Previous context: We visited the Eiffel Tower in Paris.\n"
            "Current segment: It was an amazing experience in Parry.\n"
            "Corrected text: It was an amazing experience in Paris.\n\n"
            "Now, correct the following segment using the provided context:\n\n"
            f"{context}\n\n"
            f"Current segment to correct: {seg['text']}\n\n"
            "Output only the corrected text of the current segment. Do not include any additional explanations, comments, or content.\n"
        )
        try:
            corrected_text = chat_llm(prompt=prompt, sysprompt="You are a transcription correction expert.",model_name=model_name if model_name else None, api_key=api_key, backend=backend if backend else None, logger=logger)
        except Exception as e:
            print(f"LLM纠错异常：{e}")
            corrected_text = seg["text"]
        corrected_seg = seg.copy()
        corrected_seg["text"] = corrected_text if corrected_text else seg["text"]
        corrected_segments.append(corrected_seg)
    return corrected_segments


def should_merge(seg1, seg2, api_key, model_name=None, backend=None, logger=None):
    """
    利用 LLM 判断两个转录段是否应合并，前提是合并后时长不超过 4 秒。

    参数：
      - seg1, seg2: 待判断的两个段（字典格式）
      - openai_api_key: OpenAI API Key（不使用 Ollama 时必需）
      - use_ollama: 是否使用本地接口
      - logger: 日志记录器，可选
    """
    try:
        # prompt = (
        #     "You are an expert in subtitle optimization.\n"
        #     "Determine whether the following two transcription segments should be merged into one coherent sentence.\n"
        #     "Respond with only 'Merge' or 'Do not merge'.\n\n"
        #     f"[Segment 1] Start: {seg1['start']}s, End: {seg1['end']}s, Text: '{seg1['text']}'\n"
        #     f"[Segment 2] Start: {seg2['start']}s, End: {seg2['end']}s, Text: '{seg2['text']}'\n"
        # )
        prompt = (
            "You are an expert in optimizing video subtitles. Your task is to determine whether two transcription segments should be merged into one subtitle. "
            "Merge them only if: (1) each segment alone does not express a complete meaning and could be ambiguous or unclear, and (2) merging them forms a complete and coherent sentence. "
            "If each segment can stand alone with a clear meaning (even if not a full sentence), do not merge them. "
            "Consider the context and semantics carefully.\n\n"
            "Here are some examples to guide you:\n"
            "Example 1:\n"
            "[Segment 1] Text: '你们在干'\n"
            "[Segment 2] Text: '什么'\n"
            "Result: 'Merge' (Reason: '你们在干' and '什么' are incomplete alone; together they form '你们在干什么', a complete question.)\n\n"
            "Example 2:\n"
            "[Segment 1] Text: '小明昨天吃了人'\n"
            "[Segment 2] Text: '参，非常补'\n"
            "Result: 'Merge' (Reason: '小明昨天吃了人' is ambiguous and alarming alone; '参，非常补' is incomplete; together they form '小明昨天吃了人参，非常补', a clear sentence.)\n\n"
            "Example 3:\n"
            "[Segment 1] Text: '我刚才跑步去了'\n"
            "[Segment 2] Text: '所以有点累'\n"
            "Result: 'Do not merge' (Reason: '我刚才跑步去了' and '所以有点累' each express a clear meaning independently.)\n\n"
            "Example 4:\n"
            "[Segment 1] Text: '他在看'\n"
            "[Segment 2] Text: '电视'\n"
            "Result: 'Merge' (Reason: '他在看' is incomplete and unclear; '电视' alone lacks context; together they form '他在看电视', a complete sentence.)\n\n"
            "Example 5:\n"
            "[Segment 1] Text: '今天天气很好'\n"
            "[Segment 2] Text: '适合出去玩'\n"
            "Result: 'Do not merge' (Reason: Both '今天天气很好' and '适合出去玩' are clear and meaningful independently.)\n\n"
            "Now, determine whether the following two segments should be merged:\n"
            f"[Segment 1] Start time: {seg1['start']} seconds, End time: {seg1['end']} seconds, Text: '{seg1['text']}'\n"
            f"[Segment 2] Start time: {seg2['start']} seconds, End time: {seg2['end']} seconds, Text: '{seg2['text']}'\n"
            "Respond with only 'Merge' or 'Do not merge'."
        )
        answer = chat_llm(prompt=prompt, sysprompt="You are a subtitle optimization expert.",model_name=model_name if model_name else None, api_key=api_key, backend=backend if backend else None, logger=logger)
        if answer and ("not" in answer.lower() or "不" in answer):
            return False
        return True
    except Exception as e:
        print(f"判断合并异常：{e}")
        return False


def llm_merge_segments(segments, api_key, model_name=None, backend=None, logger=None):
    """
    依次判断相邻转录段是否可合并（合并后总时长不超过4秒）。
    如果某个段的文本为空，则不进行合并判断。

    参数：
      - segments: 转录段列表（字典列表）
      - openai_api_key: OpenAI API Key（不使用 Ollama 时必需）
      - use_ollama: 是否使用本地接口
      - logger: 日志记录器，可选
    返回：
      - 合并后的段列表
    """
    if not segments:
        return segments
    i = 0
    total = len(segments) - 1
    pbar = tqdm(total=total, desc="合并进度")
    while i < len(segments) - 1:
        seg1 = segments[i]
        seg2 = segments[i + 1]

        # 如果任一段的文本为空，则不尝试合并，直接跳过该对段落的合并判断
        if not seg1.get("text", "").strip() or not seg2.get("text", "").strip():
            i += 1
            pbar.update(1)
            continue

        if seg2["end"] - seg1["start"] > 4:
            i += 1
            pbar.update(1)
            continue

        if should_merge(seg1, seg2, model_name=model_name, api_key=api_key, backend=backend, logger=logger):
            merged_seg = seg1.copy()
            merged_seg["text"] = seg1["text"].strip() + " " + seg2["text"].strip()
            merged_seg["end"] = seg2["end"]
            segments[i] = merged_seg
            segments.pop(i + 1)
            pbar.update(1)
        else:
            i += 1
            pbar.update(1)
    pbar.close()
    return segments
