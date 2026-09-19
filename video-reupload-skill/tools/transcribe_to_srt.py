"""优化的 Whisper 转写脚本

用法：
  python transcribe_to_srt.py <video_file> <output_srt> [model_name_or_path]
  
示例：
  python transcribe_to_srt.py source.mp4 transcript.en.srt
  python transcribe_to_srt.py source.mp4 transcript.en.srt faster-whisper-small.en
  python transcribe_to_srt.py source.mp4 transcript.en.srt D:\path\to\model
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def transcribe_to_srt(
    video_path: Path,
    output_path: Path,
    model_name_or_path: str = "small.en",
) -> None:
    """使用 faster-whisper 转写视频为 SRT"""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit(
            "找不到 faster-whisper 库\n"
            "请安装: pip install faster-whisper"
        )
    
    if not video_path.exists():
        raise SystemExit(f"视频文件不存在: {video_path}")
    
    # 确定模型路径
    root = Path(__file__).resolve().parents[1]
    models_dir = root / "models"
    
    # 尝试本地模型
    local_model = models_dir / model_name_or_path
    if local_model.exists():
        model_path = str(local_model)
        print(f"使用本地模型: {model_path}")
    elif Path(model_name_or_path).exists():
        model_path = str(Path(model_name_or_path).resolve())
        print(f"使用指定模型: {model_path}")
    else:
        model_path = model_name_or_path
        print(f"使用模型名称: {model_path}")
    
    print(f"加载模型...")
    try:
        model = WhisperModel(model_path, device="auto", compute_type="auto")
    except Exception as e:
        raise SystemExit(f"加载模型失败: {e}")
    
    print(f"开始转写: {video_path.name}")
    print(f"  大小: {video_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    segments, info = model.transcribe(
        str(video_path),
        language="en",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )
    
    print(f"  语言: {info.language} (置信度: {info.language_probability:.2%})")
    print(f"  预计时长: {info.duration:.1f}s")
    print(f"\n生成字幕...")
    
    srt_blocks: list[str] = []
    cue_number = 1
    
    for segment in segments:
        start = format_timestamp(segment.start)
        end = format_timestamp(segment.end)
        text = segment.text.strip()
        
        if not text:
            continue
        
        block = f"{cue_number}\n{start} --> {end}\n{text}"
        srt_blocks.append(block)
        cue_number += 1
        
        if cue_number % 100 == 0:
            print(f"  已处理 {cue_number} 条字幕...", end="\r")
    
    output_path.write_text(
        "\n\n".join(srt_blocks) + "\n",
        encoding="utf-8-sig",
        newline="\n",
    )
    
    print(f"\n✓ 转写完成: {output_path}")
    print(f"  共 {len(srt_blocks)} 条字幕")


def format_timestamp(seconds: float) -> str:
    """格式化时间戳为 SRT 格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="视频转 SRT 字幕")
    parser.add_argument("video_file", type=Path, help="视频文件路径")
    parser.add_argument("output_srt", type=Path, help="输出 SRT 文件路径")
    parser.add_argument(
        "model",
        nargs="?",
        default="faster-whisper-small.en",
        help="模型名称或路径（默认: faster-whisper-small.en）",
    )
    args = parser.parse_args()
    
    transcribe_to_srt(args.video_file, args.output_srt, args.model)


if __name__ == "__main__":
    main()
