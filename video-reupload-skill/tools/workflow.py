"""视频搬运工作流 - 主流程编排（优化版）

用法：
  python workflow.py init <video_url> [--title TITLE] [--download]
  python workflow.py download <project_id>         # 下载视频
  python workflow.py transcribe <project_id>       # 语音转写
  python workflow.py translate <project_id> [--auto]
  python workflow.py build <project_id>            # 生成双语字幕
  python workflow.py archive <project_id>          # 归档完成项目
  python workflow.py status [project_id]           # 查看项目状态
  python workflow.py list [--archived]             # 列出所有项目
  python workflow.py run <project_id>              # 一键运行所有步骤
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = ROOT / "projects"
ARCHIVE_DIR = ROOT / "archive" / "ready"
MODELS_DIR = ROOT / "models"


def get_project_dir(project_id: str, archived: bool = False) -> Path:
    """获取项目目录"""
    base_dir = ARCHIVE_DIR if archived else PROJECTS_DIR
    project_dir = base_dir / project_id
    if not project_dir.exists():
        raise SystemExit(f"项目不存在: {project_id}")
    return project_dir


def load_manifest(project_dir: Path) -> dict[str, Any]:
    """加载项目清单"""
    manifest_path = project_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"找不到 manifest.json: {project_dir}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def save_manifest(project_dir: Path, manifest: dict[str, Any]) -> None:
    """保存项目清单"""
    manifest_path = project_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def extract_video_id(url: str) -> str | None:
    """从 URL 提取视频 ID"""
    # YouTube
    youtube_patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in youtube_patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # Bilibili
    bilibili_match = re.search(r"bilibili\.com/video/(BV[a-zA-Z0-9]+)", url)
    if bilibili_match:
        return bilibili_match.group(1)
    
    return None


def cmd_init(args: argparse.Namespace) -> None:
    """初始化新项目"""
    video_url = args.video_url
    video_id = extract_video_id(video_url)
    
    if not video_id:
        # 使用时间戳作为项目 ID
        video_id = datetime.now().strftime("proj_%Y%m%d_%H%M%S")
        print(f"无法从 URL 提取 ID，使用生成的项目 ID: {video_id}")
    
    project_dir = PROJECTS_DIR / video_id
    if project_dir.exists():
        raise SystemExit(f"项目已存在: {video_id}")
    
    project_dir.mkdir(parents=True, exist_ok=True)
    
    manifest = {
        "project_id": video_id,
        "video_url": video_url,
        "title": args.title or video_id,
        "created_at": datetime.now().isoformat(),
        "status": "initialized",
        "stages": {
            "download": "pending",
            "transcribe": "pending",
            "translate": "pending",
            "build": "pending",
        },
        "files": {},
        "metadata": {
            "language": "en",
            "translation_language": "zh",
            "whisper_model": "faster-whisper-small.en",
        },
    }
    
    save_manifest(project_dir, manifest)
    print(f"✓ 项目已初始化: {video_id}")
    print(f"  目录: {project_dir}")
    print(f"  标题: {manifest['title']}")
    
    # 自动下载
    if args.download:
        print(f"\n开始下载视频...")
        args.project_id = video_id
        cmd_download(args)
    else:
        print(f"\n下一步:")
        print(f"  1. 下载视频: python workflow.py download {video_id}")
        print(f"     或手动放入: {project_dir / 'source.mp4'}")


def cmd_download(args: argparse.Namespace) -> None:
    """下载视频"""
    project_dir = get_project_dir(args.project_id)
    manifest = load_manifest(project_dir)
    
    video_url = manifest["video_url"]
    output_file = project_dir / "source.mp4"
    
    if output_file.exists():
        print(f"视频文件已存在: {output_file}")
        return
    
    print(f"下载视频: {manifest['title']}")
    print(f"  URL: {video_url}")
    
    try:
        import yt_dlp
    except ImportError:
        print("✗ 未安装 yt-dlp")
        print("  安装: pip install yt-dlp")
        print(f"  或手动下载并放入: {output_file}")
        sys.exit(1)
    
    manifest["stages"]["download"] = "in_progress"
    manifest["status"] = "downloading"
    save_manifest(project_dir, manifest)
    
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(output_file),
        "quiet": False,
        "no_warnings": False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            manifest["metadata"]["duration"] = info.get("duration")
            manifest["metadata"]["uploader"] = info.get("uploader")
            if not manifest.get("title") or manifest["title"] == manifest["project_id"]:
                manifest["title"] = info.get("title", manifest["project_id"])
        
        manifest["stages"]["download"] = "completed"
        manifest["files"]["source"] = "source.mp4"
        manifest["status"] = "downloaded"
        save_manifest(project_dir, manifest)
        
        print(f"✓ 下载完成")
        print(f"\n下一步: python workflow.py transcribe {args.project_id}")
        
    except Exception as e:
        manifest["stages"]["download"] = "failed"
        manifest["status"] = "download_failed"
        save_manifest(project_dir, manifest)
        print(f"✗ 下载失败: {e}")
        sys.exit(1)


def cmd_transcribe(args: argparse.Namespace) -> None:
    """语音转写"""
    project_dir = get_project_dir(args.project_id)
    manifest = load_manifest(project_dir)
    
    source_video = project_dir / "source.mp4"
    output_srt = project_dir / "transcript.en.srt"
    
    if not source_video.exists():
        raise SystemExit(f"找不到视频文件: {source_video}")
    
    if output_srt.exists() and not args.force:
        print(f"字幕文件已存在: {output_srt}")
        print(f"  如需重新转写，添加 --force 参数")
        return
    
    print(f"转写视频: {manifest['title']}")
    
    # 调用转写脚本
    model_name = manifest["metadata"].get("whisper_model", "faster-whisper-small.en")
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "transcribe_to_srt.py"),
        str(source_video),
        str(output_srt),
        model_name,
    ]
    
    manifest["stages"]["transcribe"] = "in_progress"
    manifest["status"] = "transcribing"
    save_manifest(project_dir, manifest)
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        manifest["stages"]["transcribe"] = "completed"
        manifest["files"]["transcript"] = "transcript.en.srt"
        manifest["status"] = "transcribed"
        
        # 统计字幕数量
        if output_srt.exists():
            content = output_srt.read_text(encoding="utf-8-sig")
            cue_count = len([line for line in content.split("\n") if line.strip().isdigit()])
            manifest["metadata"]["cue_count"] = cue_count
        
        save_manifest(project_dir, manifest)
        print(f"✓ 转写完成")
        print(f"\n下一步: python workflow.py translate {args.project_id}")
    else:
        manifest["stages"]["transcribe"] = "failed"
        save_manifest(project_dir, manifest)
        print(f"✗ 转写失败")
        sys.exit(1)


def cmd_translate(args: argparse.Namespace) -> None:
    """翻译字幕"""
    project_dir = get_project_dir(args.project_id)
    manifest = load_manifest(project_dir)
    
    transcript_srt = project_dir / "transcript.en.srt"
    output_tsv = project_dir / "translation.zh.tsv"
    
    if not transcript_srt.exists():
        raise SystemExit(f"找不到英文字幕: {transcript_srt}")
    
    print(f"翻译字幕: {manifest['title']}")
    print(f"  选项:")
    print(f"    1. 自动翻译: --auto（需联网，可能不准确）")
    print(f"    2. 手动翻译: 编辑 {output_tsv}")
    print(f"       格式: cue_id<TAB>中文翻译")
    
    if args.auto:
        # 调用自动翻译
        cmd = [
            sys.executable,
            str(ROOT / "tools" / "make_bilingual_srt.py"),
            str(transcript_srt),
            str(output_tsv),
        ]
        
        manifest["stages"]["translate"] = "in_progress"
        manifest["status"] = "translating"
        manifest["metadata"]["translation_method"] = "auto"
        save_manifest(project_dir, manifest)
        
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            manifest["stages"]["translate"] = "completed"
            manifest["files"]["translation"] = "translation.zh.tsv"
            manifest["status"] = "translated"
            save_manifest(project_dir, manifest)
            print(f"✓ 翻译完成")
            print(f"\n下一步: python workflow.py build {args.project_id}")
        else:
            manifest["stages"]["translate"] = "failed"
            save_manifest(project_dir, manifest)
            print(f"✗ 翻译失败")
            sys.exit(1)
    else:
        # 生成待翻译模板
        try:
            sys.path.insert(0, str(ROOT / "tools"))
            from build_srt import parse_srt
            cues = parse_srt(transcript_srt.read_text(encoding="utf-8-sig"))
            lines = [f"{i+1}\t" for i in range(len(cues))]
            output_tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception as e:
            print(f"✗ 生成模板失败: {e}")
            sys.exit(1)
        
        manifest["stages"]["translate"] = "pending_manual"
        manifest["files"]["translation"] = "translation.zh.tsv"
        manifest["metadata"]["translation_method"] = "manual"
        manifest["status"] = "awaiting_translation"
        save_manifest(project_dir, manifest)
        
        print(f"✓ 已生成翻译模板: {output_tsv}")
        print(f"  请编辑该文件，完成后运行: python workflow.py build {args.project_id}")


def cmd_build(args: argparse.Namespace) -> None:
    """生成双语字幕"""
    project_dir = get_project_dir(args.project_id)
    manifest = load_manifest(project_dir)
    
    transcript_srt = project_dir / "transcript.en.srt"
    translation_tsv = project_dir / "translation.zh.tsv"
    output_srt = project_dir / "bilingual.srt"
    
    if not transcript_srt.exists():
        raise SystemExit(f"找不到英文字幕: {transcript_srt}")
    if not translation_tsv.exists():
        raise SystemExit(f"找不到翻译文件: {translation_tsv}")
    
    print(f"生成双语字幕: {manifest['title']}")
    
    # 调用字幕合成脚本
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "build_srt.py"),
        str(transcript_srt),
        str(translation_tsv),
        str(output_srt),
    ]
    
    manifest["stages"]["build"] = "in_progress"
    manifest["status"] = "building"
    save_manifest(project_dir, manifest)
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        manifest["stages"]["build"] = "completed"
        manifest["files"]["bilingual"] = "bilingual.srt"
        manifest["status"] = "completed"
        manifest["completed_at"] = datetime.now().isoformat()
        save_manifest(project_dir, manifest)
        print(f"✓ 双语字幕生成完成: {output_srt}")
        print(f"\n项目完成！")
        print(f"  归档: python workflow.py archive {args.project_id}")
    else:
        manifest["stages"]["build"] = "failed"
        save_manifest(project_dir, manifest)
        print(f"✗ 生成失败")
        sys.exit(1)


def cmd_archive(args: argparse.Namespace) -> None:
    """归档完成项目"""
    project_dir = get_project_dir(args.project_id)
    manifest = load_manifest(project_dir)
    
    if manifest["status"] != "completed":
        print(f"警告: 项目状态为 '{manifest['status']}'，未完成")
        if not args.force:
            print(f"  如需强制归档，添加 --force 参数")
            sys.exit(1)
    
    # 创建归档目录
    archive_name = manifest.get("title", manifest["project_id"])
    # 清理文件名中的非法字符
    archive_name = re.sub(r'[<>:"/\\|?*]', '_', archive_name)
    archive_path = ARCHIVE_DIR / archive_name
    
    if archive_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = ARCHIVE_DIR / f"{archive_name}_{timestamp}"
    
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"归档项目: {manifest['title']}")
    print(f"  从: {project_dir}")
    print(f"  到: {archive_path}")
    
    try:
        shutil.move(str(project_dir), str(archive_path))
        print(f"✓ 归档完成")
    except Exception as e:
        print(f"✗ 归档失败: {e}")
        sys.exit(1)


def cmd_run(args: argparse.Namespace) -> None:
    """一键运行完整流程"""
    project_id = args.project_id
    
    print(f"=== 开始完整流程: {project_id} ===\n")
    
    # 1. 下载（如果需要）
    project_dir = get_project_dir(project_id)
    manifest = load_manifest(project_dir)
    
    if manifest["stages"]["download"] != "completed":
        print("步骤 1/4: 下载视频")
        args_download = argparse.Namespace(project_id=project_id)
        cmd_download(args_download)
        print()
    
    # 2. 转写
    if manifest["stages"]["transcribe"] != "completed":
        print("步骤 2/4: 语音转写")
        args_transcribe = argparse.Namespace(project_id=project_id, force=False)
        cmd_transcribe(args_transcribe)
        print()
    
    # 3. 翻译
    if manifest["stages"]["translate"] != "completed":
        print("步骤 3/4: 字幕翻译")
        if args.auto_translate:
            args_translate = argparse.Namespace(project_id=project_id, auto=True)
            cmd_translate(args_translate)
            print()
        else:
            print("  需要人工翻译，生成模板...")
            args_translate = argparse.Namespace(project_id=project_id, auto=False)
            cmd_translate(args_translate)
            print("  请完成翻译后再次运行: python workflow.py run {project_id}")
            return
    
    # 4. 生成
    if manifest["stages"]["build"] != "completed":
        print("步骤 4/4: 生成双语字幕")
        args_build = argparse.Namespace(project_id=project_id)
        cmd_build(args_build)
    
    print(f"\n=== 流程完成 ===")


def cmd_status(args: argparse.Namespace) -> None:
    """显示项目状态"""
    if args.project_id:
        project_dir = get_project_dir(args.project_id)
        manifest = load_manifest(project_dir)
        print(f"\n项目: {manifest['project_id']}")
        print(f"标题: {manifest['title']}")
        print(f"URL: {manifest.get('video_url', 'N/A')}")
        print(f"状态: {manifest['status']}")
        print(f"创建时间: {manifest['created_at']}")
        if "completed_at" in manifest:
            print(f"完成时间: {manifest['completed_at']}")
        
        print(f"\n阶段:")
        stage_names = {
            "download": "下载",
            "transcribe": "转写",
            "translate": "翻译",
            "build": "生成",
        }
        for stage, status in manifest["stages"].items():
            icon = "✓" if status == "completed" else "○" if status == "pending" else "▶"
            stage_name = stage_names.get(stage, stage)
            print(f"  {icon} {stage_name}: {status}")
        
        print(f"\n文件:")
        for name, path in manifest.get("files", {}).items():
            exists = "✓" if (project_dir / path).exists() else "✗"
            file_path = project_dir / path
            size = f"{file_path.stat().st_size / 1024 / 1024:.1f} MB" if file_path.exists() else ""
            print(f"  {exists} {name}: {path} {size}")
        
        print(f"\n元数据:")
        metadata = manifest.get("metadata", {})
        if "cue_count" in metadata:
            print(f"  字幕条数: {metadata['cue_count']}")
        if "duration" in metadata:
            duration = metadata["duration"]
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            print(f"  时长: {minutes}:{seconds:02d}")
        if "whisper_model" in metadata:
            print(f"  模型: {metadata['whisper_model']}")
    else:
        cmd_list(args)


def cmd_list(args: argparse.Namespace) -> None:
    """列出所有项目"""
    base_dir = ARCHIVE_DIR if args.archived else PROJECTS_DIR
    dir_name = "归档项目" if args.archived else "活跃项目"
    
    if not base_dir.exists():
        print(f"{dir_name}目录不存在")
        return
    
    projects = sorted(base_dir.iterdir())
    if not projects:
        print(f"没有找到{dir_name}")
        return
    
    print(f"\n{dir_name} ({len(projects)} 个):\n")
    for project_dir in projects:
        if not project_dir.is_dir():
            continue
        try:
            manifest = load_manifest(project_dir)
            status = manifest["status"]
            title = manifest.get("title", manifest["project_id"])
            cue_count = manifest.get("metadata", {}).get("cue_count", "?")
            status_icon = "✓" if status == "completed" else "▶" if "in_progress" in status else "○"
            print(f"  {status_icon} {manifest['project_id'][:20]:<20} | {title[:40]:<40} | {cue_count:>4} cues | {status}")
        except Exception as e:
            print(f"  ✗ {project_dir.name} (无效项目)")


def main() -> None:
    # 设置控制台输出编码
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    
    parser = argparse.ArgumentParser(description="视频搬运工作流")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # init
    init_parser = subparsers.add_parser("init", help="初始化新项目")
    init_parser.add_argument("video_url", help="视频 URL")
    init_parser.add_argument("--title", help="视频标题")
    init_parser.add_argument("--download", action="store_true", help="立即下载")
    
    # download
    download_parser = subparsers.add_parser("download", help="下载视频")
    download_parser.add_argument("project_id", help="项目 ID")
    
    # transcribe
    transcribe_parser = subparsers.add_parser("transcribe", help="语音转写")
    transcribe_parser.add_argument("project_id", help="项目 ID")
    transcribe_parser.add_argument("--force", action="store_true", help="强制重新转写")
    
    # translate
    translate_parser = subparsers.add_parser("translate", help="翻译字幕")
    translate_parser.add_argument("project_id", help="项目 ID")
    translate_parser.add_argument("--auto", action="store_true", help="自动翻译")
    
    # build
    build_parser = subparsers.add_parser("build", help="生成双语字幕")
    build_parser.add_argument("project_id", help="项目 ID")
    
    # archive
    archive_parser = subparsers.add_parser("archive", help="归档完成项目")
    archive_parser.add_argument("project_id", help="项目 ID")
    archive_parser.add_argument("--force", action="store_true", help="强制归档未完成项目")
    
    # run
    run_parser = subparsers.add_parser("run", help="一键运行完整流程")
    run_parser.add_argument("project_id", help="项目 ID")
    run_parser.add_argument("--auto-translate", action="store_true", help="使用自动翻译")
    
    # status
    status_parser = subparsers.add_parser("status", help="查看项目状态")
    status_parser.add_argument("project_id", nargs="?", help="项目 ID（可选）")
    
    # list
    list_parser = subparsers.add_parser("list", help="列出所有项目")
    list_parser.add_argument("--archived", action="store_true", help="列出归档项目")
    
    args = parser.parse_args()
    
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    
    if args.command == "init":
        cmd_init(args)
    elif args.command == "download":
        cmd_download(args)
    elif args.command == "transcribe":
        cmd_transcribe(args)
    elif args.command == "translate":
        cmd_translate(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "archive":
        cmd_archive(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
