import os

def format_timestamp(seconds):
    """
    将秒数转换为 SRT 格式时间字符串 HH:MM:SS,mmm
    """
    total_seconds = int(seconds)
    millis = int(round((seconds - total_seconds) * 1000))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def format_ass_timestamp(seconds):
    """
    将秒数转换为 ASS 字幕格式时间字符串 H:MM:SS.cc，其中 cc 表示百分之一秒
    """
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    centiseconds = int((seconds - total_seconds) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

def group_overlapping_segments(segments):
    """
    将时间上有重叠的段归为一组，用于字幕块显示。

    参数：
      - segments: 已按起始时间排序的段列表

    返回：
      - groups: 分组后的列表
    """
    groups = []
    current_group = []
    current_end = 0
    for seg in segments:
        if not current_group:
            current_group.append(seg)
            current_end = seg["end"]
        else:
            if seg["start"] < current_end:
                current_group.append(seg)
                current_end = max(current_end, seg["end"])
            else:
                groups.append(current_group)
                current_group = [seg]
                current_end = seg["end"]
    if current_group:
        groups.append(current_group)
    return groups

def generate_srt(segments, output_path):
    """
    根据段列表生成 SRT 字幕文件；相同时间段的多个说话人各自换行显示。

    参数：
      - segments: 包含 "start", "end", "text", "speaker"（可选）的段列表
      - output_path: 输出 SRT 文件路径
    """
    segments = sorted(segments, key=lambda x: x["start"])
    groups = group_overlapping_segments(segments)
    lines = []
    index = 1
    for group in groups:
        group_start = min(seg["start"] for seg in group)
        group_end = max(seg["end"] for seg in group)
        text_lines = []
        for seg in group:
            if seg.get("speaker"):
                text_lines.append(f"{seg['speaker']}: {seg['text']}")
            else:
                text_lines.append(seg['text'])
        text = "\n".join(text_lines)
        lines.append(str(index))
        lines.append(f"{format_timestamp(group_start)} --> {format_timestamp(group_end)}")
        lines.append(text)
        lines.append("")
        index += 1
    srt_content = "\n".join(lines)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        print(f"SRT 字幕文件已保存到 {output_path}")
    except Exception as e:
        print(f"生成 SRT 文件失败：{e}")

def generate_ass(segments, output_path):
    """
    根据段列表生成 ASS 字幕文件。

    参数：
      - segments: 包含 "start", "end", "text", "speaker"（可选）的段列表
      - output_path: 输出 ASS 文件路径
    """
    segments = sorted(segments, key=lambda x: x["start"])
    groups = group_overlapping_segments(segments)
    header = (
        "[Script Info]\n"
        "Title: Video Subtitle ASS File\n"
        "ScriptType: v4.00+\n"
        "Collisions: Normal\n"
        "PlayResX: 1920\n"
        "PlayResY: 1080\n"
        "Timer: 100.0000\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = []
    for group in groups:
        group_start = min(seg["start"] for seg in group)
        group_end = max(seg["end"] for seg in group)
        text_lines = []
        for seg in group:
            if seg.get("speaker"):
                text_lines.append(f"{seg['speaker']}: {seg['text']}")
            else:
                text_lines.append(seg["text"])
        text = "\\N".join(text_lines)
        start_time = format_ass_timestamp(group_start)
        end_time = format_ass_timestamp(group_end)
        event_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}"
        events.append(event_line)
    ass_content = header + "\n".join(events)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
        print(f"ASS 字幕文件已保存到 {output_path}")
    except Exception as e:
        print(f"生成 ASS 文件失败：{e}")
