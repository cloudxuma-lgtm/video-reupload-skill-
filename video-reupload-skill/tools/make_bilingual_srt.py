"""Create a bilingual SRT from an English SRT using a protected glossary."""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass
class Cue:
    number: str
    timing: str
    text: str


# Longest phrases must be protected first. These are standard translations for
# the mechanism-design and auction terminology used in this lecture.
GLOSSARY = [
    ("subgame-perfect equilibrium", "子博弈精炼均衡"),
    ("subgame perfect equilibrium", "子博弈精炼均衡"),
    ("revenue equivalence", "收入等价"),
    ("incentive compatibility", "激励相容性"),
    ("incentive compatible", "激励相容的"),
    ("participation constraint", "参与约束"),
    ("individual rationality", "个体理性"),
    ("revelation principle", "显示原理"),
    ("dominant strategy", "占优策略"),
    ("first-price auction", "一价拍卖"),
    ("second-price auction", "二价拍卖"),
    ("ad exchange", "广告交易所"),
    ("mechanism design", "机制设计"),
    ("dynamic mechanism", "动态机制"),
    ("private information", "私人信息"),
    ("independent private values", "独立私人价值"),
    ("common value", "共同价值"),
    ("game theory", "博弈论"),
    ("strategy-proof", "策略无关"),
    ("truth-telling", "真实报告"),
    ("truthful reporting", "真实报告"),
    ("social welfare", "社会福利"),
    ("allocation rule", "分配规则"),
    ("budget balance", "预算平衡"),
    ("private value", "私人价值"),
    ("credible mechanism", "可信机制"),
    ("Nash equilibrium", "纳什均衡"),
    ("equilibrium", "均衡"),
    ("incentive", "激励"),
    ("mechanism", "机制"),
    ("auction", "拍卖"),
    ("auctioneer", "拍卖人"),
    ("bidder", "竞标者"),
    ("bid", "出价"),
    ("seller", "卖方"),
    ("buyer", "买方"),
    ("allocation", "分配"),
    ("utility", "效用"),
    ("payoff", "收益"),
    ("valuation", "估值"),
    ("revenue", "收入"),
    ("welfare", "福利"),
    ("screening", "筛选"),
    ("signaling", "信号传递"),
    ("Bayesian", "贝叶斯"),
    ("ex post", "事后"),
    ("interim", "中间"),
    ("ex ante", "事前"),
    ("credible", "可信的"),
]


def parse_srt(raw: str) -> list[Cue]:
    blocks = re.split(r"\r?\n\r?\n+", raw.strip())
    cues: list[Cue] = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        cues.append(Cue(lines[0].strip(), lines[1].strip(), " ".join(lines[2:]).strip()))
    if not cues:
        raise ValueError("No valid SRT cues found")
    return cues


def protect_terms(text: str, batch_id: int) -> tuple[str, dict[str, str]]:
    protected: dict[str, str] = {}
    result = text
    for term_index, (term, translation) in enumerate(GLOSSARY):
        token = f"ZXTERM{batch_id:04d}{term_index:03d}ZX"
        pattern = re.compile(r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])", re.IGNORECASE)
        if pattern.search(result):
            result = pattern.sub(token, result)
            protected[token] = translation
    return result, protected


def marker_pattern(marker: str) -> re.Pattern[str]:
    return re.compile(r"\s*".join(map(re.escape, marker)), re.IGNORECASE)


def restore_terms(text: str, protected: dict[str, str]) -> str:
    result = text
    for token, translation in protected.items():
        result = marker_pattern(token).sub(translation, result)
    corrections = {
        "机构设计": "机制设计",
        "激励兼容性": "激励相容性",
        "激励兼容": "激励相容",
        "优势策略": "占优策略",
        "主导策略": "占优策略",
        "均衡性": "均衡",
        "可靠机制": "可信机制",
        "私人资讯": "私人信息",
        "私有信息": "私人信息",
        "显示原则": "显示原理",
    }
    for old, new in corrections.items():
        result = result.replace(old, new)
    return re.sub(r"\s+", " ", result).strip()


def translate_request(text: str, retries: int = 6) -> str:
    query = urlencode({"q": text, "langpair": "en|zh-CN"})
    url = f"https://api.mymemory.translated.net/get?{query}"
    request = Request(url, headers={"User-Agent": "Codex bilingual subtitle tool/1.0"})
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("responseStatus") != 200:
                raise RuntimeError(payload.get("responseDetails") or "translation service error")
            return payload["responseData"]["translatedText"]
        except (HTTPError, URLError, TimeoutError, RuntimeError, KeyError, json.JSONDecodeError) as error:
            last_error = error
            if attempt + 1 < retries:
                time.sleep(min(45, 2 ** attempt))
    raise RuntimeError(f"Translation failed after {retries} attempts: {last_error}")


def split_translated_batch(translated: str, markers: list[str]) -> list[str] | None:
    positions: list[tuple[int, int]] = []
    for marker in markers:
        match = marker_pattern(marker).search(translated)
        if not match:
            return None
        positions.append((match.start(), match.end()))
    parts: list[str] = []
    for index, (_, end) in enumerate(positions):
        next_start = positions[index + 1][0] if index + 1 < len(positions) else len(translated)
        parts.append(translated[end:next_start].strip(" \t\r\n:;，。"))
    return parts


def batches(cues: list[Cue], max_chars: int = 320, max_items: int = 8) -> Iterable[list[Cue]]:
    current: list[Cue] = []
    size = 0
    for cue in cues:
        next_size = size + len(cue.text) + 22
        if current and (next_size > max_chars or len(current) >= max_items):
            yield current
            current = []
            size = 0
        current.append(cue)
        size += len(cue.text) + 22
    if current:
        yield current


def translate_cues(cues: list[Cue]) -> list[str]:
    translations: list[str] = []
    total = sum(1 for _ in batches(cues))
    for batch_number, batch in enumerate(batches(cues), start=1):
        protected_texts: list[str] = []
        protected_all: dict[str, str] = {}
        markers: list[str] = []
        for cue in batch:
            protected, terms = protect_terms(cue.text, batch_number)
            protected_texts.append(protected)
            protected_all.update(terms)
            markers.append(f"ZXCUE{batch_number:04d}{len(markers):03d}ZX")
        query_text = " ".join(
            f"{text} {marker}" for text, marker in zip(protected_texts, markers)
        )
        translated = translate_request(query_text)
        parts = split_translated_batch(translated, markers)
        if parts is None or len(parts) != len(batch):
            # Smaller requests are more reliable when a service drops a marker.
            parts = []
            for cue_index, (text, marker) in enumerate(zip(protected_texts, markers)):
                single = translate_request(f"{text} {marker}")
                one = split_translated_batch(single, [marker])
                parts.append(one[0] if one else single.replace(marker, "").strip())
        translations.extend(restore_terms(part, protected_all) for part in parts)
        print(f"Translated batch {batch_number}/{total}", flush=True)
        time.sleep(0.25)
    return translations


def write_bilingual(path: Path, cues: list[Cue], translations: list[str]) -> None:
    blocks = []
    for cue, translation in zip(cues, translations):
        blocks.append(f"{cue.number}\n{cue.timing}\n{cue.text}\n{translation}")
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    cues = parse_srt(args.input.read_text(encoding="utf-8-sig"))
    translations = translate_cues(cues)
    write_bilingual(args.output, cues, translations)
    print(f"Wrote {len(cues)} cues to {args.output}")


if __name__ == "__main__":
    main()
