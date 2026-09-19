# GitHub 发布信息

## 推荐仓库名

```text
video-reupload-skill
```

## GitHub 仓库简介（Description）

```text
Codex skill and CLI workflow for creating Chinese bilingual subtitles from authorized English videos.
```

## 中文简介

```text
用于将已获授权的英文视频制作成中文字幕的 Codex skill 和命令行工作流，支持下载、Whisper 转写、人工或自动翻译、双语 SRT 生成、状态追踪和归档。
```

## 推荐 Topics

```text
codex-skill
video-subtitles
subtitle-translation
faster-whisper
yt-dlp
chinese-subtitles
bilingual-subtitles
academic-video
```

## 手动上传方式

1. 在 GitHub 创建名为 `video-reupload-skill` 的空仓库。
2. 将本目录中的全部文件上传到仓库根目录。
3. 不要上传 `projects/`、`models/`、`archive/`、视频文件或个人素材。

## Git 命令方式

在本目录打开 PowerShell：

```powershell
git init
git add .
git commit -m "Initial release of video-reupload skill"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/video-reupload-skill.git
git push -u origin main
```

将 `YOUR_USERNAME` 替换为你的 GitHub 用户名。
