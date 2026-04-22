from __future__ import annotations

import re
import zlib
from pathlib import Path
from typing import List


class _Page:
    def __init__(self, text: str = ""):
        self._text = text

    def extract_text(self):
        return self._text


def _decode_pdf_literal(raw: bytes) -> str:
    raw = raw.replace(rb"\(", b"(").replace(rb"\)", b")").replace(rb"\n", b"\n")
    raw = re.sub(rb"\\([0-7]{1,3})", lambda m: bytes([int(m.group(1), 8)]), raw)
    try:
        return raw.decode("utf-8")
    except Exception:
        return raw.decode("latin-1", errors="ignore")


def _decode_pdf_hex(raw: bytes) -> str:
    hex_part = re.sub(rb"\s+", b"", raw)
    if len(hex_part) % 2 == 1:
        hex_part += b"0"
    try:
        data = bytes.fromhex(hex_part.decode("ascii", errors="ignore"))
    except Exception:
        return ""
    if not data:
        return ""

    # 常见情况：中文文本以 UTF-16BE 形式出现
    if len(data) >= 2 and b"\x00" in data[:8]:
        try:
            return data.decode("utf-16-be", errors="ignore")
        except Exception:
            pass
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return data.decode("latin-1", errors="ignore")


def _extract_text_from_stream(stream_bytes: bytes) -> str:
    parts: List[str] = []
    for m in re.finditer(rb"\((.*?)(?<!\\)\)\s*Tj", stream_bytes, re.S):
        text = _decode_pdf_literal(m.group(1)).strip()
        if text:
            parts.append(text)

    # 处理 TJ 数组中的字符串，例如 [(中) 120 (文)] TJ 或 [<4e2d> <6587>] TJ
    for arr in re.finditer(rb"\[(.*?)\]\s*TJ", stream_bytes, re.S):
        seg = arr.group(1)
        tmp = []
        for lit in re.finditer(rb"\((.*?)(?<!\\)\)", seg, re.S):
            txt = _decode_pdf_literal(lit.group(1)).strip()
            if txt:
                tmp.append(txt)
        for hx in re.finditer(rb"<([0-9A-Fa-f\s]+)>", seg, re.S):
            txt = _decode_pdf_hex(hx.group(1)).strip()
            if txt:
                tmp.append(txt)
        if tmp:
            parts.append("".join(tmp))

    for m in re.finditer(rb"<([0-9A-Fa-f\s]+)>\s*Tj", stream_bytes, re.S):
        text = _decode_pdf_hex(m.group(1)).strip()
        if text:
            parts.append(text)

    return "\n".join(parts)


class PdfReader:
    def __init__(self, path: str):
        data = Path(path).read_bytes()
        self.pages: List[_Page] = []

        streams = list(re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S))
        chunks: List[str] = []
        for stream_match in streams:
            raw_stream = stream_match.group(1)
            header_window = data[max(0, stream_match.start() - 200) : stream_match.start()]
            decoded_stream = raw_stream
            if b"/FlateDecode" in header_window:
                try:
                    decoded_stream = zlib.decompress(raw_stream)
                except Exception:
                    decoded_stream = raw_stream

            extracted = _extract_text_from_stream(decoded_stream)
            if extracted.strip():
                chunks.append(extracted)

        if chunks:
            self.pages = [_Page("\n".join(chunks))]
        else:
            self.pages = []
