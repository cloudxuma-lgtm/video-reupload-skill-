"""通用字幕合成脚本 - 替代硬编码的 build_*_outputs.py

用法：
  python build_srt.py <english_srt> <translation_tsv> <output_srt>
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Cue:
    """字幕条目"""
    number: int
    timing: str
    text: str


def parse_srt(raw: str) -> list[Cue]:
    """解析 SRT 文件"""
    blocks = [
        block
        for block in re.split(r"\r?\n\r?\n+", raw.strip())
        if block.strip()
    ]
    
    cues: list[Cue] = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3 or not lines[0].isdigit() or "-->" not in lines[1]:
            print(f"警告: 跳过无效的 SRT 块: {block[:100]!r}", file=sys.stderr)
            continue
        
        number = int(lines[0])
        timing = lines[1].strip()
        text = " ".join(lines[2:]).strip()
        cues.append(Cue(number, timing, text))
    
    # 检查编号连续性
    ids = [cue.number for cue in cues]
    if ids != list(range(1, len(cues) + 1)):
        print(f"警告: 字幕编号不连续", file=sys.stderr)
    
    return cues


def load_translations(path: Path) -> dict[int, str]:
    """加载翻译文件（TSV 格式）"""
    translations: dict[int, str] = {}
    
    for line_num, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        
        parts = line.split("\t", 1)
        if len(parts) != 2:
            raise SystemExit(
                f"翻译文件格式错误 (行 {line_num}): 应为 'cue_id<TAB>translation'\n"
                f"实际内容: {line!r}"
            )
        
        cue_id_str, translation = parts
        
        if not cue_id_str.isdigit():
            raise SystemExit(
                f"翻译文件格式错误 (行 {line_num}): cue_id 必须是数字\n"
                f"实际值: {cue_id_str!r}"
            )
        
        cue_id = int(cue_id_str)
        translation = translation.strip()
        
        if not translation:
            print(f"警告: cue {cue_id} 的翻译为空", file=sys.stderr)
        
        if cue_id in translations:
            raise SystemExit(f"翻译文件包含重复的 cue_id: {cue_id}")
        
        translations[cue_id] = translation
    
    return translations


def validate_coverage(cues: list[Cue], translations: dict[int, str]) -> None:
    """验证翻译覆盖率"""
    expected = set(range(1, len(cues) + 1))
    actual = set(translations.keys())
    
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    
    if missing or extra:
        if missing:
            print(f"错误: 缺少以下 cue 的翻译: {missing}", file=sys.stderr)
        if extra:
            print(f"错误: 翻译包含多余的 cue: {extra}", file=sys.stderr)
        raise SystemExit("翻译覆盖率不完整")


def build_bilingual_srt(
    cues: list[Cue],
    translations: dict[int, str],
    output_path: Path,
) -> None:
    """生成双语 SRT"""
    blocks: list[str] = []
    
    for cue in cues:
        translation = translations[cue.number]
        block = f"{cue.number}\n{cue.timing}\n{cue.text}\n{translation}"
        blocks.append(block)
    
    output_path.write_text(
        "\n\n".join(blocks) + "\n",
        encoding="utf-8-sig",
        newline="\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="生成双语 SRT 字幕")
    parser.add_argument("english_srt", type=Path, help="英文 SRT 文件")
    parser.add_argument("translation_tsv", type=Path, help="翻译 TSV 文件")
    parser.add_argument("output_srt", type=Path, help="输出的双语 SRT 文件")
    args = parser.parse_args()
    
    if not args.english_srt.exists():
        raise SystemExit(f"找不到英文字幕: {args.english_srt}")
    
    if not args.translation_tsv.exists():
        raise SystemExit(f"找不到翻译文件: {args.translation_tsv}")
    
    print(f"解析英文字幕: {args.english_srt}")
    cues = parse_srt(args.english_srt.read_text(encoding="utf-8-sig"))
    print(f"  找到 {len(cues)} 条字幕")
    
    print(f"加载翻译: {args.translation_tsv}")
    translations = load_translations(args.translation_tsv)
    print(f"  找到 {len(translations)} 条翻译")
    
    print(f"验证覆盖率...")
    validate_coverage(cues, translations)
    print(f"  ✓ 覆盖率完整")
    
    print(f"生成双语字幕: {args.output_srt}")
    build_bilingual_srt(cues, translations, args.output_srt)
    print(f"  ✓ 完成")


if __name__ == "__main__":
    main()
