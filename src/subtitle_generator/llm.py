import time
from datetime import datetime
from openai import OpenAI

def chat_with_ollama(prompt, sysprompt='', model="huihui_ai/qwen2.5-1m-abliterated:7b", max_attempts=5, logger=None):
    """
    使用本地 Ollama 模型进行对话，采用指数退避策略。

    参数：
      - prompt: 用户输入文本
      - sysprompt: 系统提示（例如角色设定）
      - model: 模型名称
      - max_attempts: 最大重试次数
      - logger: 日志记录器，可选
    返回：
      - 返回模型回复文本（字符串），若失败则返回空字符串。
    """
    import ollama
    attempts = 0
    sleep_time = 1
    while attempts < max_attempts:
        try:
            start_time = datetime.now()
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": sysprompt},
                    {"role": "user", "content": prompt},
                ]
            )
            response_text = response['message']['content'].strip()
            end_time = datetime.now()
            if logger:
                duration = (end_time - start_time).total_seconds()
                log_message = (
                    f"Model: {model}\nStart: {start_time}\nEnd: {end_time}\nDuration: {duration:.2f} s\n"
                    f"Prompt:\n{prompt}\nResponse:\n{response_text}\n{'='*50}"
                )
                logger.info(log_message)
            return response_text
        except Exception as e:
            attempts += 1
            print(f"Ollama 调用失败（尝试 {attempts}/{max_attempts}）：{e}")
            time.sleep(sleep_time)
            sleep_time *= 2
    print("达到最大尝试次数，返回空字符串")
    return ""

def chatwith_gpt(prompt, sysprompt='', model="gpt-4o", api_key='', max_attempts=5, logger=None):
    """
    使用 OpenAI GPT 模型进行对话，采用指数退避策略。

    参数：
      - prompt: 用户输入文本
      - sysprompt: 系统提示
      - model: 模型名称
      - api_key: OpenAI API Key
      - max_attempts: 最大重试次数
      - logger: 日志记录器，可选
    返回：
      - 返回模型回复文本（字符串），若失败则返回空字符串。
    """
    if not api_key:
        import os
        api_key = os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=api_key)
    attempts = 0
    sleep_time = 1
    while attempts < max_attempts:
        try:
            start_time = datetime.now()
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sysprompt},
                    {"role": "user", "content": prompt},
                ],
            )
            response_text = completion.choices[0].message.content.strip()
            end_time = datetime.now()
            if logger:
                duration = (end_time - start_time).total_seconds()
                log_message = (
                    f"Model: {model}\nStart: {start_time}\nEnd: {end_time}\nDuration: {duration:.2f} s\n"
                    f"Prompt:\n{prompt}\nResponse:\n{response_text}\n{'='*50}"
                )
                logger.info(log_message)
            return response_text
        except Exception as e:
            attempts += 1
            print(f"GPT 调用失败（尝试 {attempts}/{max_attempts}）：{e}")
            time.sleep(sleep_time)
            sleep_time *= 2
    return ""

def chat_llm(prompt, sysprompt='', model_name=None, api_key='', backend="gpt", max_attempts=5, logger=None):
    """
    统一封装 LLM 对话接口，根据 backend 参数调用对应的接口。
    
    参数：
      - prompt: 用户输入文本
      - sysprompt: 系统提示信息（例如专家角色说明）
      - model_name: 模型名称。如为 None 则根据 backend 默认选择：
            * 若 backend 为 "ollama"，默认模型为 "huihui_ai/qwen2.5-1m-abliterated:7b"
            * 若 backend 为 "gpt"，默认模型为 "gpt-4o"
      - api_key: OpenAI API Key（当 backend 为 gpt 时需要）
      - backend: 选择使用的 LLM 接口，可取 "gpt" 或 "ollama"（以后可以扩展更多）
      - max_attempts: 最大重试次数
      - logger: 日志记录器，可选
    
    返回：
      - LLM 回复的文本（字符串）；调用失败则返回空字符串。
    """
    if backend and isinstance(backend, str) and "ollama" in backend.lower():
        if not model_name:
            model_name = "huihui_ai/qwen2.5-1m-abliterated:7b"
        return chat_with_ollama(prompt=prompt, sysprompt=sysprompt, model=model_name, max_attempts=max_attempts, logger=logger)
    else:  # 默认采用 "gpt"
        if not model_name:
            model_name = "gpt-4o"
        return chatwith_gpt(prompt=prompt, sysprompt=sysprompt, model=model_name, api_key=api_key, max_attempts=max_attempts, logger=logger)
