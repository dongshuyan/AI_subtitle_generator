import os
from moviepy.video.io.VideoFileClip import VideoFileClip

def extract_audio_from_video(video_path, audio_output_path):
    """
    从视频中提取音频并保存为 WAV 格式（16kHz，单声道）。

    参数：
      - video_path: 输入视频文件路径
      - audio_output_path: 输出音频文件路径

    异常：
      - 若视频文件不存在或提取失败，则抛出异常。
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    try:
        print("提取视频音频……")
        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(
            audio_output_path,
            fps=16000,
            codec='pcm_s16le',
            ffmpeg_params=["-ac", "1"],
            logger=None
        )
        clip.close()
        print(f"音频已保存到 {audio_output_path}")
    except Exception as e:
        raise RuntimeError(f"提取音频失败: {e}")
