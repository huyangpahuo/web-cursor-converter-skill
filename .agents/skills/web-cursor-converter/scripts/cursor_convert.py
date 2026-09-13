# -*- coding: utf-8 -*-
"""
把 Windows 光标包(.ani 动画 / .cur 静态)转换成网页可用的 PNG 帧序列。

浏览器不支持 .ani 动画光标(CSS cursor 只接受静态 .cur/.png),思路:
  1. .ani 是 RIFF 容器,内部每个 "icon" 子块是一个完整的 .cur(含热点坐标);
  2. 逐帧解出 .cur,用 Pillow 转 RGBA、缩放到目标尺寸,存为 PNG;
  3. 生成 data.js 记录每个状态的帧列表、每帧时长与热点,
     前端 JS 按它用 CSS 变量逐帧切换,实现动画光标
     (配套前端模板见本 skill 的 assets/)。

用法:
  python cursor_convert.py <光标包目录> <输出目录> [尺寸px=32]

输出:
  <输出目录>/<state>/<i>.png   各状态帧图
  <输出目录>/data.js           window.WEB_CURSOR = {...}
"""

import io
import json
import os
import re
import shutil
import struct
import sys

from PIL import Image

# 文件名(不含扩展名,小写匹配)-> 前端状态名(对应 CSS cursor 关键字)
# 光标包命名五花八门,这里收集常见别名;没匹配到的文件以文件名小写作为状态名
STATE_ALIASES = {
    "normal": ["normal", "arrow", "pointer", "default", "regular", "aero_arrow", "cursor"],
    "link": ["link", "link_select", "linkselect", "hand", "hand_select", "handselect", "alternate", "alternate_select"],
    "text": ["text", "text_select", "textselect", "ibeam", "beam", "hardwriting"],
    "busy": ["busy", "wait", "hourglass"],
    "working": ["working", "working_background", "background", "app_starting", "appstarting"],
    "unavailable": ["unavailable", "unavralible", "no", "no_select", "blocked", "cross"],
    "help": ["help", "help_select"],
    "move": ["move", "move_select", "sizeall", "all_scroll", "allscroll", "drag"],
    "crosshair": ["crosshair", "precision", "precision_select", "cell"],
    "ew": ["horizontal", "ew", "ew_resize", "size_we", "col_resize", "resize_left_right"],
    "ns": ["vertical", "ns", "ns_resize", "size_ns", "row_resize", "resize_up_down"],
    "nwse": ["nwse", "nwse_resize", "size_nwse", "diagonal_1", "resize_1", "resize_left_up"],
    "nesw": ["nesw", "nesw_resize", "size_nesw", "diagonal_2", "resize_2", "resize_left_down"],
}

# 反查表:小写别名 -> 状态名
ALIAS_LOOKUP = {alias: state for state, aliases in STATE_ALIASES.items() for alias in aliases}


def resolve_state(stem):
    return ALIAS_LOOKUP.get(stem.lower(), re.sub(r"[^a-z0-9_-]+", "-", stem.lower()).strip("-") or "cursor")


def read_chunks(data, start=12, end=None):
    """遍历 RIFF 块,返回 [(块ID, body偏移, body大小)]"""
    end = len(data) if end is None else end
    pos = start
    out = []
    while pos + 8 <= end:
        cid = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        out.append((cid, pos + 8, size))
        pos += 8 + size + (size & 1)  # RIFF 块按字对齐
    return out


def parse_ani(path):
    """解析 .ani,返回 (帧列表[bytes,每个是完整.cur], 每帧毫秒列表)"""
    data = open(path, "rb").read()
    if data[:4] != b"RIFF" or data[8:12] != b"ACON":
        raise ValueError("%s 不是 ANI 文件" % path)

    frames, rate, seq, default_rate = [], None, None, None
    for cid, off, size in read_chunks(data):
        if cid == b"anih":
            hdr = struct.unpack("<9I", data[off:off + 36])
            default_rate = hdr[6]  # 单位 jiffie(1/60 秒)
        elif cid == b"rate":
            rate = list(struct.unpack("<%dI" % (size // 4), data[off:off + size]))
        elif cid == b"seq ":
            seq = list(struct.unpack("<%dI" % (size // 4), data[off:off + size]))
        elif cid == b"LIST" and data[off:off + 4] == b"fram":
            body = data[off + 4:off + size]
            for sub_id, sub_off, sub_size in read_chunks(body, start=0):
                if sub_id == b"icon":
                    frames.append(body[sub_off:sub_off + sub_size])

    if seq:
        frames = [frames[i] for i in seq if i < len(frames)]
    ms = [round(r * 1000.0 / 60.0) for r in (rate or [default_rate or 6])]
    return frames, ms


def parse_cur(data):
    """解析 .cur/.ico(取其中最大的一帧),返回 (PIL.Image, 热点x, 热点y)。

    图像交给 Pillow 的 ICO 插件解码(它处理 ICO 内嵌 BMP 高度双倍的问题);
    热点自己从 ICONDIRENTRY 读:wPlanes/wBitCount 字段被复用为热点 x/y,
    千万不要按名字去别的偏移找(那是踩过的坑)。
    """
    count = struct.unpack("<H", data[4:6])[0]
    best = None
    hx = hy = 0
    for i in range(count):
        entry = data[6 + i * 16: 6 + (i + 1) * 16]
        x_hot, y_hot, bytes_res = struct.unpack("<HHI", entry[4:12])
        if best is None or bytes_res > best:
            best = bytes_res
            hx, hy = x_hot, y_hot
    img = Image.open(io.BytesIO(data))
    img.load()
    return img.convert("RGBA"), hx, hy


def convert(src_dir, out_dir, size=32):
    states = {}
    os.makedirs(out_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith((".ani", ".cur")))
    if not files:
        print("错误:%s 里没有 .ani/.cur 文件" % src_dir)
        sys.exit(1)

    for fn in files:
        stem, ext = os.path.splitext(fn)
        state = resolve_state(stem)
        path = os.path.join(src_dir, fn)

        if ext.lower() == ".ani":
            frames, ms = parse_ani(path)
        else:
            frames, ms = [open(path, "rb").read()], [100]

        state_dir = os.path.join(out_dir, state)
        # 两个源文件映射到同一状态时,先清空避免旧帧残留
        if os.path.isdir(state_dir):
            shutil.rmtree(state_dir)
        os.makedirs(state_dir, exist_ok=True)

        urls, hot, frame_ms, orig = [], None, [], None
        for i, cur in enumerate(frames):
            img, hx, hy = parse_cur(cur)
            if orig is None:
                orig = img.size
            scale = size / max(img.size)
            if scale != 1:
                img = img.resize(
                    (max(1, round(img.width * scale)), max(1, round(img.height * scale))),
                    Image.LANCZOS,
                )
            hot = (min(round(hx * scale), size), min(round(hy * scale), size))
            name = "%d.png" % i
            img.save(os.path.join(state_dir, name), optimize=True)
            urls.append("%s/%s" % (state, name))
            frame_ms.append(ms[i] if i < len(ms) else ms[-1])

        states[state] = {
            "frames": urls,
            "ms": frame_ms[0],
            "hotspot": list(hot),
            "size": size,
        }
        print("%-24s -> %-12s %2d 帧  原始 %sx%s  热点 %s  每帧 %dms" %
              (fn, state, len(urls), orig[0], orig[1], hot, frame_ms[0]))

    data_js = (
        "/* 由 web-cursor-converter skill 的 cursor_convert.py 生成,请勿手改 */\n"
        "window.WEB_CURSOR = " + json.dumps(states, ensure_ascii=False) + ";\n"
    )
    with open(os.path.join(out_dir, "data.js"), "w", encoding="utf-8") as f:
        f.write(data_js)

    total = sum(len(s["frames"]) for s in states.values())
    print("\n完成:%d 个状态,共 %d 帧 -> %s" % (len(states), total, out_dir))
    print("前端接入:复制本 skill assets/ 下的 cursor-template.css/.js,")
    print("把 CSS 里的资源基路径替换为站点路径,<body> 末尾先引 data.js 再引 cursor.js。")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 32)
