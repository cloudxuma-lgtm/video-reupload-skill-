# 视频搬运 Skill

将 YouTube/Bilibili 等平台的英文视频添加中文字幕，用于搬运学术讲座、技术分享到中文平台。

## 适用场景

- 为英文学术讲座、技术分享视频添加中文字幕
- 批量处理视频的语音转写和翻译
- 需要可追溯、可恢复、可审查的字幕制作工作流
- 经济学、数学、博弈论等专业内容的准确翻译

## 核心能力

1. **视频下载** - 自动下载 YouTube/Bilibili 视频（基于 yt-dlp）
2. **语音转写** - 使用 faster-whisper 将英文音频转为 SRT 字幕
3. **字幕翻译** - 支持自动翻译（MyMemory API）或人工翻译
4. **双语字幕生成** - 合成英文和中文字幕为标准双语 SRT
5. **项目管理** - 每个视频独立项目，完整的元数据和状态追踪
6. **质量检查** - 自动验证字幕连续性、翻译覆盖率

## 快速开始

### 方式一：完全自动化（适合测试）

```powershell
# 初始化并下载
python tools\workflow.py init "https://youtube.com/watch?v=xxxxx" --title "视频标题" --download

# 一键运行（使用自动翻译）
python tools\workflow.py run <video_id> --auto-translate

# 查看结果
python tools\workflow.py status <video_id>
```

### 方式二：人工翻译（推荐用于专业内容）

```powershell
# 1. 初始化项目
python tools\workflow.py init "https://youtube.com/watch?v=xxxxx" --title "标题"

# 2. 下载视频
python tools\workflow.py download <video_id>

# 3. 语音转写
python tools\workflow.py transcribe <video_id>

# 4. 生成翻译模板
python tools\workflow.py translate <video_id>

# 5. 人工翻译（编辑 projects\<video_id>\translation.zh.tsv）

# 6. 生成双语字幕
python tools\workflow.py build <video_id>

# 7. 归档项目
python tools\workflow.py archive <video_id>
```

## 详细用法

### 1. 初始化项目

```powershell
# 基本用法
python tools\workflow.py init "https://youtube.com/watch?v=xxxxx"

# 指定标题
python tools\workflow.py init "视频URL" --title "陶哲轩：AI时代的数学"

# 初始化并立即下载
python tools\workflow.py init "视频URL" --title "标题" --download
```

**支持的平台：**
- YouTube（自动提取视频ID）
- Bilibili（自动提取BV号）
- 其他平台（使用时间戳作为项目ID）

**项目结构：**
```
projects/<video_id>/
├── manifest.json          # 项目元数据
├── source.mp4            # 源视频
├── transcript.en.srt     # 英文字幕
├── translation.zh.tsv    # 中文翻译
└── bilingual.srt         # 双语字幕
```

### 2. 下载视频

```powershell
python tools\workflow.py download <video_id>
```

**依赖：** pip install yt-dlp

**注意：**
- 自动选择最佳画质（优先mp4格式）
- 会自动提取视频标题和时长信息
- 如果下载失败，可以手动下载并重命名为 source.mp4 放入项目目录

### 3. 语音转写

```powershell
# 基本用法
python tools\workflow.py transcribe <video_id>

# 强制重新转写
python tools\workflow.py transcribe <video_id> --force
```

**模型配置：**
- 默认：aster-whisper-small.en（精度与速度平衡）
- 位置：D:\codex-workspace\TTS\models\faster-whisper-small.en
- 可在 manifest.json 中修改 metadata.whisper_model

**模型选择建议：**
- 	iny.en - 最快，适合初步测试
- ase.en - 快速，日常使用
- small.en - **推荐**，精度与速度平衡
- medium.en - 高精度，速度较慢
- large-v3 - 最高精度，非常慢

**优化：**
- 使用 VAD（语音活动检测）自动跳过静音段
- 支持 GPU 加速（需安装 CUDA 版本的 PyTorch）

### 4. 翻译字幕

#### 方式一：自动翻译（快速但不准确）

```powershell
python tools\workflow.py translate <video_id> --auto
```

使用 MyMemory API 自动翻译。

**注意：**
- 自动翻译对专业术语不友好
- 建议仅用于测试或非专业内容
- 翻译后仍需人工校对

#### 方式二：人工翻译（推荐）

```powershell
python tools\workflow.py translate <video_id>
```

生成翻译模板 	ranslation.zh.tsv：

```tsv
1	[在此填写第1条字幕的中文翻译]
2	[在此填写第2条字幕的中文翻译]
3	[在此填写第3条字幕的中文翻译]
```

**格式要求：**
- 每行格式：<cue_id><TAB><中文翻译>
- 必须覆盖所有字幕条目
- 支持分段翻译（见下文）

#### 分段翻译工作流（推荐用于长视频）

对于 1000+ 条字幕的长视频：

```powershell
# 1. 生成完整模板
python tools\workflow.py translate <video_id>

# 2. 拆分为多个文件（手工或脚本）
cd projects\<video_id>
# 创建：
#   translation.001-150.tsv
#   translation.151-300.tsv
#   translation.301-450.tsv
#   ...

# 3. 逐段翻译（使用AI助手或人工）

# 4. 合并所有分段
Get-Content translation.*.tsv | Set-Content translation.zh.tsv

# 5. 验证并生成字幕
cd ..\..
python tools\workflow.py build <video_id>
```

**专业术语处理：**

编辑 	ools\make_bilingual_srt.py 添加术语表：

```python
GLOSSARY = [
    ("mechanism design", "机制设计"),
    ("Nash equilibrium", "纳什均衡"),
    ("Bayesian persuasion", "贝叶斯劝服"),
    ("optimal transport", "最优传输"),
    # 添加你的术语...
]
```

### 5. 生成双语字幕

```powershell
python tools\workflow.py build <video_id>
```

生成 ilingual.srt，格式为：

```srt
1
00:00:00,000 --> 00:00:05,000
Hello and welcome to this lecture.
你好，欢迎来到本次讲座。

2
00:00:05,500 --> 00:00:10,000
Today we will discuss mechanism design.
今天我们将讨论机制设计。
```

### 6. 查看项目状态

```powershell
# 查看所有项目
python tools\workflow.py list

# 查看归档项目
python tools\workflow.py list --archived

# 查看特定项目详情
python tools\workflow.py status <video_id>
```

**状态输出示例：**
```
项目: xxxxx
标题: 陶哲轩：AI时代的数学
URL: https://youtube.com/watch?v=xxxxx
状态: completed
创建时间: 2026-09-19T10:30:00
完成时间: 2026-09-19T12:45:00

阶段:
  ✓ 下载: completed
  ✓ 转写: completed
  ✓ 翻译: completed
  ✓ 生成: completed

文件:
  ✓ source: source.mp4 125.3 MB
  ✓ transcript: transcript.en.srt 
  ✓ translation: translation.zh.tsv 
  ✓ bilingual: bilingual.srt 

元数据:
  字幕条数: 515
  时长: 64:30
  模型: faster-whisper-small.en
```

### 7. 归档完成项目

```powershell
# 归档完成的项目
python tools\workflow.py archive <video_id>

# 强制归档未完成项目
python tools\workflow.py archive <video_id> --force
```

项目将移动到 rchive\ready\<视频标题>\

### 8. 一键运行（自动化流程）

```powershell
# 需要人工翻译（会在翻译步骤停止）
python tools\workflow.py run <video_id>

# 使用自动翻译（完全自动）
python tools\workflow.py run <video_id> --auto-translate
```

自动执行：下载 → 转写 → 翻译 → 生成

## 命令速查

| 命令 | 说明 |
|------|------|
| init <url> [--title] [--download] | 初始化新项目 |
| download <id> | 下载视频 |
| 	ranscribe <id> [--force] | 语音转写 |
| 	ranslate <id> [--auto] | 字幕翻译 |
| uild <id> | 生成双语字幕 |
| rchive <id> [--force] | 归档项目 |
| un <id> [--auto-translate] | 一键运行 |
| status [id] | 查看状态 |
| list [--archived] | 列出项目 |

## 高级技巧

### 使用 AI 助手批量翻译

```powershell
# 1. 生成翻译模板
python tools\workflow.py translate <video_id>

# 2. 使用 Codex/ChatGPT 翻译
# 提示词示例：
# "这是一段经济学讲座的字幕，请翻译为中文，保持专业术语准确：
#  [粘贴 50-100 条英文字幕]
#  输出格式：cue_id<TAB>翻译"

# 3. 将翻译结果追加到 translation.zh.tsv
# 4. 重复直到完成所有字幕
```

### 批量处理多个视频

```powershell
# 批量初始化
 = @(
    "https://youtube.com/watch?v=video1",
    "https://youtube.com/watch?v=video2",
    "https://youtube.com/watch?v=video3"
)
foreach ( in ) {
    python tools\workflow.py init  --download
}

# 批量转写
Get-ChildItem projects -Directory | ForEach-Object {
    python tools\workflow.py transcribe .Name
}
```

### 自定义 Whisper 模型

```powershell
# 使用不同模型
cd projects\<video_id>
# 编辑 manifest.json:
# "metadata": {
#   "whisper_model": "medium.en"  # 或其他模型
# }
cd ..\..
python tools\workflow.py transcribe <video_id> --force
```

### 质量检查

```powershell
# 检查字幕连续性
python -c "from tools.build_srt import parse_srt; import sys; cues=parse_srt(open(sys.argv[1], encoding='utf-8-sig').read()); print(f'Cues: {len(cues)}'); ids=[c.number for c in cues]; print('Continuous:', ids==list(range(1,len(ids)+1)))" projects\<video_id>\transcript.en.srt

# 检查翻译覆盖率
python tools\build_srt.py projects\<video_id>\transcript.en.srt projects\<video_id>\translation.zh.tsv NUL
```

## 目录结构

```
D:\codex-workspace\TTS\
├── projects\              # 活跃项目
│   └── <video_id>\
│       ├── manifest.json
│       ├── source.mp4
│       ├── transcript.en.srt
│       ├── translation.zh.tsv
│       └── bilingual.srt
├── archive\              # 归档项目
│   └── ready\
│       ├── 陶哲轩：AI时代的数学\
│       ├── 李盛武：机制设计\
│       └── ...（已完成9个视频）
├── models\              # Whisper 模型
│   └── faster-whisper-small.en\
├── tools\               # 工具脚本
│   ├── workflow.py           # 主流程编排
│   ├── transcribe_to_srt.py  # 语音转写
│   ├── build_srt.py          # 字幕合成
│   └── make_bilingual_srt.py # 自动翻译
├── 素材\                # 原始素材
├── output\              # 其他输出
├── SKILL.md            # 本文档
├── README.md           # 快速开始
└── DESIGN.md           # 设计文档
```

## manifest.json 结构

```json
{
  "project_id": "xxxxx",
  "video_url": "https://...",
  "title": "视频标题",
  "created_at": "2026-09-19T10:30:00",
  "completed_at": "2026-09-19T12:45:00",
  "status": "completed",
  "stages": {
    "download": "completed",
    "transcribe": "completed",
    "translate": "completed",
    "build": "completed"
  },
  "files": {
    "source": "source.mp4",
    "transcript": "transcript.en.srt",
    "translation": "translation.zh.tsv",
    "bilingual": "bilingual.srt"
  },
  "metadata": {
    "language": "en",
    "translation_language": "zh",
    "whisper_model": "faster-whisper-small.en",
    "translation_method": "manual",
    "duration": 3870.8,
    "cue_count": 515,
    "uploader": "..."
  }
}
```

## 依赖安装

```bash
# 必需
pip install faster-whisper

# 可选（用于视频下载）
pip install yt-dlp

# 确保 FFmpeg 在系统 PATH 中
# Windows: 从 https://ffmpeg.org/ 下载并添加到 PATH
```

## 已完成项目示例

本 workflow 已成功完成 9 个学术视频的字幕制作：

1. **Shengwu Li (Harvard)** - 1634 cues - 博弈论讲座
2. **Aranyak Mehta: Economic Mechanisms in the GenAI Era** - 891 cues - AI与经济机制
3. **Credible Mechanism** - 1058 cues - 可信机制
4. **Daniel Litt: Working with LLMs to do high quality math** - 1775 cues - LLM数学应用
5. **Kevin Weil: AI for Mathematical and Scientific Discovery** - 1801 cues - AI科学发现
6. **Cédric Villani: Optimal Transport Theory** - 1630 cues - 最优传输理论
7. **Obviously Strategy-Proof Mechanisms** - 850 cues - 显然策略防御机制
8. **Revealed Preference Tests for Bayesian Persuasion** - 1574 cues - 贝叶斯劝服
9. **Terence Tao: Mathematics in the Age of AI** - 515 cues - AI时代的数学

## 常见问题

### Q: 转写速度慢怎么办？

A: 
1. 使用更小的模型（	iny.en 或 ase.en）
2. 如果有 GPU，安装 CUDA 版本的 PyTorch
3. VAD 已默认启用，会跳过静音段

### Q: 翻译不准确怎么办？

A: 
1. **推荐人工翻译**（专业内容必须）
2. 添加专业术语表到 	ools/make_bilingual_srt.py
3. 分段翻译，逐段用 AI 助手校对
4. 使用更好的翻译 API（DeepL、GPT-4）

### Q: 如何处理其他语言？

A: 修改 manifest.json:
```json
"metadata": {
  "language": "zh",  // 源语言
  "translation_language": "en"  // 目标语言
}
```

### Q: 如何给视频添加字幕（烧录）？

A: 使用 FFmpeg:
```powershell
ffmpeg -i source.mp4 -vf "subtitles=bilingual.srt:force_style='Fontname=Microsoft YaHei,Fontsize=16'" output.mp4
```

### Q: 下载失败怎么办？

A: 
1. 手动下载视频并重命名为 source.mp4
2. 放入 projects\<video_id>\ 目录
3. 继续运行 	ranscribe 步骤

### Q: 中文输出乱码？

A: 已在优化版中修复。如果仍有问题：
```powershell
chcp 65001  # 设置控制台为 UTF-8
python tools\workflow.py list
```

## 更新历史

- **v2.0** (2026-09-19) - 优化版
  - ✨ 新增 download 命令（yt-dlp 集成）
  - ✨ 新增 rchive 命令
  - ✨ 新增 un 命令（一键流程）
  - ✨ 改进 status 显示（文件大小、时长等）
  - ✨ 改进 list 显示（表格格式）
  - 🐛 修复 Windows 中文输出编码问题
  - 📚 完善 SKILL.md 文档

- **v1.0** (2026-09-19) - 初始版本
  - 项目管理和状态追踪
  - Whisper 转写
  - 自动/人工翻译
  - 双语字幕生成

## 作者说明

这是基于实际搬运 9 个经济学/数学学术讲座视频的经验整理而成的工作流。

专注于**字幕制作**，暂不包含 TTS 配音功能。
