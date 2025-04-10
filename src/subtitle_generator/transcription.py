import os
import time
import subprocess
import librosa
import soundfile as sf
import whisper
from tqdm import tqdm

def post_process_segments(segments):
    """
    对转录结果段落进行后处理，清除重复文本段。

    参数：
      - segments: 转录结果中的段列表，每个为字典，包含 "start", "end", "text" 等字段

    返回：
      - processed_segments: 处理后的段列表
    """
    processed_segments = []
    last_non_empty_text = None  # 记录最近的非空文本内容
    
    for segment in segments:
        current_text = segment.get("text", "").strip()
        # 如果当前段为空，则直接保留
        if not current_text:
            processed_segments.append(segment.copy())
            continue
        
        # 如果当前文本与最近的非空文本相同，则清空当前文本
        if last_non_empty_text == current_text:
            new_segment = segment.copy()
            new_segment["text"] = ""
            processed_segments.append(new_segment)
        else:
            processed_segments.append(segment.copy())
            last_non_empty_text = current_text
    return processed_segments

def run_spleeter_on_audio(audio_path):
    """
    运行 Spleeter 分离人声（调用外部 shell 脚本）。
    若成功返回处理后的人声文件路径，否则抛出异常。

    参数：
      - audio_path: 输入音频文件路径

    注意：生成的分离后文件将存放在与输入文件同一目录下，
    这样便于统一管理临时文件（例如在临时目录中处理）。
    """
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")
    
    audio_filename = os.path.basename(audio_path)
    filename_wo_ext, audio_ext = os.path.splitext(audio_filename)
    vocals_ext = audio_ext.lower() if audio_ext else ".wav"
    final_filename = f"{filename_wo_ext}-output{vocals_ext}"
    # 修改输出目录：使用输入文件所在目录，而非用户 Downloads 目录
    final_path = os.path.join(os.path.dirname(audio_path), final_filename)
    
    # 假设 run_spleeter.sh 脚本与本模块位于同一目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    shell_script_path = os.path.join(script_dir, "run_spleeter.sh")
    if not os.path.isfile(shell_script_path):
        print(f"未找到分离脚本: {shell_script_path}，跳过 spleeter 处理")
        return audio_path

    try:
        # 使用 subprocess.run 捕获输出与错误信息
        result = subprocess.run(
            ["bash", shell_script_path, audio_path],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Spleeter 输出: {result.stdout}")
        print(f"人声文件生成：{final_path}")
        return final_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"运行 run_spleeter.sh 脚本失败: {str(e)}\n错误输出: {e.stderr}")

def transcribe_audio_whisper(audio_path, notuse_spleeter=False, model_size="large-v3", device=None, language=None, model_path=None):
    """
    利用 Whisper 模型进行语音转录，流程包括：
      1. 调用 run_spleeter_on_audio 对音频进行人声分离；
      2. 使用 librosa 对分离后音频进行重采样（16kHz）及预加重处理；
      3. 加载 Whisper 模型并自动检测语言（若未指定）；
      4. 对音频转录，并返回包含转录结果、分段列表等信息的字典。

    参数：
      - audio_path: 输入音频路径
      - model_size: Whisper 模型大小
      - device: 计算设备（默认为 "cpu"）
      - language: 指定转录语言（空则自动检测）
      - model_path: 模型下载目录（可选）

    返回：
      - 转录结果字典（包含 "segments" 和 "language" 等键）
    """
    # 先进行人声分离
    if not notuse_spleeter:
        print("正在运行 Spleeter 进行人声分离……")
        processed_audio = run_spleeter_on_audio(audio_path)
        print(f"Spleeter 处理后音频文件：{processed_audio}")
    else:
        processed_audio = audio_path
    
    # 重采样及预加重处理，结果保存到与 processed_audio 同一目录下
    dirname = os.path.dirname(processed_audio)
    basename = os.path.basename(processed_audio)
    name, ext = os.path.splitext(basename)
    new_audio_path = os.path.join(dirname, f"{name}-librosa{ext}")
    try:
        audio, sr = librosa.load(processed_audio, sr=16000)
    except Exception as e:
        raise RuntimeError(f"加载或重采样音频失败：{e}")
    audio = librosa.effects.preemphasis(audio)
    try:
        sf.write(new_audio_path, audio, sr)
    except Exception as e:
        raise RuntimeError(f"写入重采样音频失败：{e}")
    print(f"音频重采样为16kHz：{new_audio_path}")
    audio_path = new_audio_path

    if device is None:
        device = "cpu"
    print(f"加载 Whisper 模型（{model_size}，设备：{device}）……")
    try:
        # 模型路径优先使用环境变量 Whisper_model_path
        model_path_env = os.getenv('Whisper_model_path')
        if model_path_env:
            model = whisper.load_model(model_size, download_root=model_path_env, device=device)
        else:
            model = whisper.load_model(model_size, device=device)
    except Exception as e:
        raise RuntimeError(f"加载 Whisper 模型失败：{e}")

    if not language:
        try:
            audio_data = whisper.load_audio(audio_path)
            audio_data = whisper.pad_or_trim(audio_data)
            mel = whisper.log_mel_spectrogram(audio_data, n_mels=model.dims.n_mels).to(model.device)
            _, probs = model.detect_language(mel)
            language = max(probs, key=probs.get)
            print(f"检测到语言：{language}")
        except Exception as e:
            raise RuntimeError(f"自动检测语言失败：{e}")

    attempts = 0
    max_attempts = 5
    while attempts < max_attempts:
        try:
            transcription_params = {
                "language": language,
                "verbose": False,
                "no_speech_threshold": 0.5,
                "condition_on_previous_text": True,
                "word_timestamps": True,
                "fp16": device != "cpu",
            }
            result = model.transcribe(audio_path, **transcription_params)
            return result
        except Exception as e:
            attempts += 1
            print(f"语音识别调用失败（尝试 {attempts}/{max_attempts}）：{e}")
            if attempts < max_attempts:
                time.sleep(5)
            else:
                raise RuntimeError("语音识别连续失败，程序终止。")
