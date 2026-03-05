# Bilibili 视频文案提取工具

一个简单的命令行工具：输入 B 站视频链接或 BV 号，提取视频字幕并导出为文案文本。

## 功能
- 支持输入 `BV号` 或完整视频 URL。
- 自动拉取视频信息与字幕列表。
- 可指定优先语言（默认 `ai-zh`）。
- 支持输出到终端，或导出为 `txt/json` 文件。

## 运行环境
- Python 3.9+
- 无第三方依赖（仅标准库）

## 使用示例
```bash
# 直接打印文案
python bilibili_copy_extractor.py https://www.bilibili.com/video/BV1xx411c7mD

# 导出为 txt
python bilibili_copy_extractor.py BV1xx411c7mD -o output.txt

# 导出为 json（包含元信息）
python bilibili_copy_extractor.py BV1xx411c7mD -o output.json --json

# 指定优先语言
python bilibili_copy_extractor.py BV1xx411c7mD --lang zh-CN
```

## 说明
- 本工具基于公开视频接口与视频字幕数据。
- 若视频无字幕，则无法直接提取完整文案。
- 默认提取首个分 P（`cid`）字幕。
