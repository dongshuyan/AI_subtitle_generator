# 文件：src/subtitle_generator/utils.py
from dataclasses import dataclass, asdict
import os

@dataclass
class Segment:
    start: float
    end: float
    text: str
    speaker: str = ""

    def to_dict(self):
        return asdict(self)

def safe_remove(filepath):
    """
    如果文件存在，则删除之。若删除失败则打印提示。

    参数：
      - filepath: 文件路径
    """
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"删除临时文件 {filepath} 失败: {e}")

def normalize_language_code_for_google(lang: str) -> str:
    """
    标准化语言代码，适用于 Google Translate 接口。

    例如，将用户可能输入的 'zh', 'chinese', 'cn' 等转换为 'zh-cn'，
    同时支持所有主流语言。

    参数：
      - lang: 用户输入的目标语言代码
    返回：
      - 标准化后的 Google Translate 使用的语言代码；如果找不到，则返回原字符串。
    """
    lang = lang.lower().strip()
    mapping = {
        "arabic": "ar",
        "ar": "ar",
        "czech": "cs",
        "cs": "cs",
        "danish": "da",
        "da": "da",
        "dutch": "nl",
        "nl": "nl",
        "english": "en",
        "en": "en",
        "finnish": "fi",
        "fi": "fi",
        "french": "fr",
        "fr": "fr",
        "german": "de",
        "de": "de",
        "greek": "el",
        "el": "el",
        "hebrew": "iw",
        "iw": "iw",    # Google 老接口代码，有时使用 'iw'
        "hindi": "hi",
        "hi": "hi",
        "hungarian": "hu",
        "hu": "hu",
        "indonesian": "id",
        "id": "id",
        "italian": "it",
        "it": "it",
        "japanese": "ja",
        "ja": "ja",
        "korean": "ko",
        "ko": "ko",
        "norwegian": "no",
        "no": "no",
        "polish": "pl",
        "pl": "pl",
        "portuguese": "pt",
        "pt": "pt",
        "romanian": "ro",
        "ro": "ro",
        "russian": "ru",
        "ru": "ru",
        "slovak": "sk",
        "sk": "sk",
        "spanish": "es",
        "es": "es",
        "swedish": "sv",
        "sv": "sv",
        "thai": "th",
        "th": "th",
        "turkish": "tr",
        "tr": "tr",
        "ukrainian": "uk",
        "uk": "uk",
        "vietnamese": "vi",
        "vi": "vi",
        "chinese": "zh-cn",
        "zh": "zh-cn",
        "zh-cn": "zh-cn",
        "zh_tw": "zh-tw",
        "taiwanese": "zh-tw"
    }
    return mapping.get(lang, lang)

def normalize_language_code_for_api(lang: str) -> str:
    """
    标准化语言代码，适用于其他 API（如 Whisper、niutrans_translate）。
    
    例如，将用户可能输入的 'zh', 'chinese', 'cn' 等转换为 'zh'，
    而非 'zh-cn'。支持主流语言，若不在映射内则返回原始输入。

    参数：
      - lang: 用户输入的目标语言代码
    返回：
      - 标准化后的 API 使用的语言代码；如果找不到，则返回原字符串。
    """
    lang = lang.lower().strip()
    mapping = {
        "arabic": "ar",
        "ar": "ar",
        "czech": "cs",
        "cs": "cs",
        "danish": "da",
        "da": "da",
        "dutch": "nl",
        "nl": "nl",
        "english": "en",
        "en": "en",
        "finnish": "fi",
        "fi": "fi",
        "french": "fr",
        "fr": "fr",
        "german": "de",
        "de": "de",
        "greek": "el",
        "el": "el",
        "hebrew": "he",  # 使用现代代码 'he'
        "he": "he",
        "hindi": "hi",
        "hi": "hi",
        "hungarian": "hu",
        "hu": "hu",
        "indonesian": "id",
        "id": "id",
        "italian": "it",
        "it": "it",
        "japanese": "ja",
        "ja": "ja",
        "korean": "ko",
        "ko": "ko",
        "norwegian": "no",
        "no": "no",
        "polish": "pl",
        "pl": "pl",
        "portuguese": "pt",
        "pt": "pt",
        "romanian": "ro",
        "ro": "ro",
        "russian": "ru",
        "ru": "ru",
        "slovak": "sk",
        "sk": "sk",
        "spanish": "es",
        "es": "es",
        "swedish": "sv",
        "sv": "sv",
        "thai": "th",
        "th": "th",
        "turkish": "tr",
        "tr": "tr",
        "ukrainian": "uk",
        "uk": "uk",
        "vietnamese": "vi",
        "vi": "vi",
        "chinese": "zh",
        "zh": "zh",
        "zh-cn": "zh",
        "zh_tw": "zh-tw",
        "taiwanese": "zh-tw"
    }
    return mapping.get(lang, lang)

def copy_video_to_temp(video_path: str) -> str:
    """
    将用户传入的视频复制到当前用户的下载目录下的
    subtitle_generator/test 目录中，并将复制后的文件名改为 test，文件后缀不变。
    如果存在同名文件则覆盖。
    返回复制后的文件路径。
    参数：
      - video_path: 原始视频路径
    返回：
      - temp_video_path: 复制后的临时视频文件完整路径
    """
    import os
    import shutil
    # 获取当前用户的下载目录（假定为 ~/Downloads）
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    # 定义目标目录：Downloads/subtitle_generator
    target_dir = os.path.join(downloads_dir, "subtitle_generator")
    # 如果目标目录不存在则创建
    os.makedirs(target_dir, exist_ok=True)
    # 获取原始文件后缀
    _, ext = os.path.splitext(os.path.basename(video_path))
    # 拼接新的文件名 "test" + 后缀
    new_file_name = f"test{ext}"
    temp_video_path = os.path.join(target_dir, new_file_name)
    try:
        shutil.copy2(video_path, temp_video_path)
        print(f"已复制视频至临时位置：{temp_video_path}")
    except Exception as e:
        raise RuntimeError(f"复制视频文件失败：{e}")
    return temp_video_path


def delete_temp_folder(temp_file_path: str):
    """
    删除包含临时文件的目录。假设该临时文件在 Downloads/subtitle_generator/test 目录中，
    删除这个 test 文件夹及其中所有文件。

    参数：
      - temp_file_path: 临时文件完整路径（用来定位所在目录）
    """
    import shutil
    # 获取目录路径
    temp_dir = os.path.dirname(temp_file_path)
    try:
        shutil.rmtree(temp_dir)
        print(f"已删除临时目录：{temp_dir}")
    except Exception as e:
        print(f"删除临时目录 {temp_dir} 失败：{e}")
