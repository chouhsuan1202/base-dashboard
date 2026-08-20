#!/usr/bin/env python3
"""從 icon.svg 光柵化出所有尺寸的 app icon。

用法：python3 make_icons.py

正本是 icon.svg（Claude design 定稿的霓虹網格版），每個尺寸都直接從 SVG 畫出來，
不是先出大圖再縮小，這是 design handoff 的硬規則。
用 headless Chrome 當光柵化引擎，因為系統內建工具不支援 SVG，
而 cairosvg 之類的套件不在標準庫裡。
"""

import base64
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SVG = ROOT / "icon.svg"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 檔名對應尺寸。iOS app 的圖示放在 xcassets 裡，換了要重編 ipa 才會生效
TARGETS = {
    ROOT / "icon-1024.png": 1024,
    ROOT / "icon-512.png": 512,
    ROOT / "icon-192.png": 192,
    ROOT / "apple-touch-icon.png": 180,
    ROOT / "ios-app/Assets.xcassets/AppIcon.appiconset/icon-1024.png": 1024,
}


def fail(msg):
    print("make_icons 失敗：" + msg, file=sys.stderr)
    raise SystemExit(1)


def main():
    if not SVG.exists():
        fail("找不到 " + str(SVG))
    if not Path(CHROME).exists():
        fail("找不到 Chrome，光柵化需要它：" + CHROME)

    b64 = base64.b64encode(SVG.read_bytes()).decode()

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for out, size in TARGETS.items():
            wrapper = tmpdir / ("wrap-%d.html" % size)
            wrapper.write_text(
                '<!doctype html><meta charset="utf-8">'
                "<style>html,body{margin:0;padding:0;background:#0b0f13}"
                "img{display:block;width:%dpx;height:%dpx}</style>"
                '<img src="data:image/svg+xml;base64,%s">' % (size, size, b64),
                encoding="utf-8",
            )
            out.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    CHROME,
                    "--headless",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    "--force-device-scale-factor=1",
                    "--window-size=%d,%d" % (size, size),
                    "--screenshot=%s" % out,
                    "--virtual-time-budget=3000",
                    wrapper.as_uri(),
                ],
                check=True,
                capture_output=True,
            )
            if not out.exists():
                fail("沒有產生 " + str(out))
            print("  %s  %dx%d" % (out.name, size, size))

    print("圖示已更新。ios-app 底下那張換了之後要重編 Base.ipa 才會出現在手機上。")


if __name__ == "__main__":
    main()
