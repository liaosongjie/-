#!/usr/bin/env python3
"""提取 Bilibili 视频文案（优先字幕）的命令行工具。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class VideoMeta:
    bvid: str
    aid: int
    cid: int
    title: str


class BilibiliExtractor:
    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout

    def _get_json(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if params:
            url = f"{url}?{urlencode(params)}"
        req = Request(
            url,
            headers={"User-Agent": USER_AGENT, "Referer": "https://www.bilibili.com"},
        )
        with urlopen(req, timeout=self.timeout) as resp:
            content = resp.read().decode("utf-8")
        return json.loads(content)

    def parse_bvid(self, text: str) -> str:
        text = text.strip()
        matched = re.search(r"(BV[0-9A-Za-z]{10})", text)
        if matched:
            return matched.group(1)

        parsed = urlparse(text)
        if parsed.netloc and parsed.path:
            matched = re.search(r"(BV[0-9A-Za-z]{10})", parsed.path)
            if matched:
                return matched.group(1)

        raise ValueError("无法识别 BV 号，请输入 BV 号或视频 URL。")

    def get_video_meta(self, bvid: str) -> VideoMeta:
        api = "https://api.bilibili.com/x/web-interface/view"
        payload = self._get_json(api, {"bvid": bvid})

        if payload.get("code") != 0:
            raise RuntimeError(f"查询视频信息失败: {payload.get('message', '未知错误')}")

        data = payload["data"]
        pages = data.get("pages") or []
        if not pages:
            raise RuntimeError("未找到分P信息，无法确定 cid。")

        return VideoMeta(
            bvid=data["bvid"],
            aid=int(data["aid"]),
            cid=int(pages[0]["cid"]),
            title=data["title"],
        )

    def get_subtitles(self, meta: VideoMeta) -> list[dict[str, Any]]:
        api = "https://api.bilibili.com/x/player/v2"
        payload = self._get_json(api, {"bvid": meta.bvid, "cid": meta.cid})

        if payload.get("code") != 0:
            raise RuntimeError(f"查询字幕信息失败: {payload.get('message', '未知错误')}")

        subtitle_data = payload.get("data", {}).get("subtitle", {})
        return subtitle_data.get("subtitles", [])

    def download_subtitle_body(self, subtitle_url: str) -> list[dict[str, Any]]:
        if subtitle_url.startswith("//"):
            subtitle_url = f"https:{subtitle_url}"

        payload = self._get_json(subtitle_url)

        body = payload.get("body")
        if not isinstance(body, list):
            raise RuntimeError("字幕格式异常：未找到 body 列表。")
        return body

    @staticmethod
    def body_to_text(body: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for item in body:
            content = str(item.get("content", "")).strip()
            if content:
                lines.append(content)
        return "\n".join(lines)


def save_output(path: Path, text: str, as_json: bool = False, metadata: dict[str, Any] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if as_json:
        payload = {
            "metadata": metadata or {},
            "text": text,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        path.write_text(text, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="提取 Bilibili 视频文案（字幕文本）")
    parser.add_argument("input", help="BV 号或视频 URL")
    parser.add_argument("-o", "--output", help="输出文件路径，默认打印到终端")
    parser.add_argument("--lang", default="ai-zh", help="优先字幕语言代码，如 ai-zh / zh-CN")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式写入输出文件")
    return parser


def pick_subtitle(subtitles: list[dict[str, Any]], lang: str) -> dict[str, Any]:
    if not subtitles:
        raise RuntimeError("该视频没有可用字幕，无法直接提取文案。")

    exact = [item for item in subtitles if item.get("lan") == lang]
    if exact:
        return exact[0]

    zh_like = [item for item in subtitles if str(item.get("lan", "")).startswith("zh") or "中文" in str(item.get("lan_doc", ""))]
    if zh_like:
        return zh_like[0]

    return subtitles[0]


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    extractor = BilibiliExtractor()

    try:
        bvid = extractor.parse_bvid(args.input)
        meta = extractor.get_video_meta(bvid)
        subtitles = extractor.get_subtitles(meta)
        selected = pick_subtitle(subtitles, args.lang)
        body = extractor.download_subtitle_body(selected["subtitle_url"])
        text = extractor.body_to_text(body)
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"网络请求失败: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"提取失败: {exc}", file=sys.stderr)
        return 1

    output = args.output
    if output:
        metadata = {
            "title": meta.title,
            "bvid": meta.bvid,
            "aid": meta.aid,
            "cid": meta.cid,
            "lang": selected.get("lan"),
            "lang_doc": selected.get("lan_doc"),
        }
        save_output(Path(output), text, as_json=args.json, metadata=metadata)
        print(f"已导出: {output}")
    else:
        print(f"# {meta.title}\n")
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
