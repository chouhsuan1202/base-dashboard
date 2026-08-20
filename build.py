#!/usr/bin/env python3
"""把 data.json 注入 template.html，產生 dashboard.html。

用法：python3 build.py
只用 Python 3 標準庫，沒有外部依賴。
dashboard.html 是產出物，不要手改，改 data.json 或 template.html 之後重跑本腳本。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data.json"
TEMPLATE = ROOT / "template.html"
OUTPUT = ROOT / "dashboard.html"
INDEX = ROOT / "index.html"
PLACEHOLDER = "/*__DATA__*/"

# 全站禁用字元：em dash 與 en dash
BANNED = {"\u2014": "em dash", "\u2013": "en dash"}

# 每餐可標的營養類別，要跟 template.html 裡的 NUT 對應
NUTRI_KEYS = ["protein", "veg", "fruit", "grain", "dairy"]

REQUIRED_CONFIG = [
    "start_date",
    "baseline_kg",
    "weekly_loss_kg",
    "horizon_weeks",
    "goal_kg",
    "budget_kcal",
    "budget_pending_bmr",
    "gym_per_week",
    "phase",
]


def fail(msg):
    print("build 失敗：" + msg, file=sys.stderr)
    raise SystemExit(1)


def load_data():
    try:
        raw = DATA.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail("找不到 " + str(DATA))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        fail("data.json 不是合法 JSON：" + str(err))

    config = data.get("config")
    if not isinstance(config, dict):
        fail("data.json 缺少 config 物件")
    missing = [k for k in REQUIRED_CONFIG if k not in config]
    if missing:
        fail("config 缺少欄位：" + ", ".join(missing))

    entries = data.get("entries")
    if not isinstance(entries, list):
        fail("data.json 缺少 entries 陣列")
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or "date" not in entry:
            fail("entries[%d] 缺少 date 欄位" % i)
        meals = entry.get("meals", [])
        if not isinstance(meals, list):
            fail("entries[%d] 的 meals 必須是陣列" % i)
        for j, meal in enumerate(meals):
            where = "entries[%d].meals[%d]" % (i, j)
            nutri = meal.get("nutri", [])
            if not isinstance(nutri, list):
                fail(where + " 的 nutri 必須是陣列")
            bad = [n for n in nutri if n not in NUTRI_KEYS]
            if bad:
                fail(
                    where
                    + " 的 nutri 有不認識的值："
                    + ", ".join(map(str, bad))
                    + "，只能用 "
                    + ", ".join(NUTRI_KEYS)
                )
            if "junk" in meal and not isinstance(meal["junk"], bool):
                fail(where + " 的 junk 必須是 true 或 false")
            if meal.get("junk") and nutri:
                fail(where + " 同時標了 junk 與 nutri，兩者只能擇一")

    entries.sort(key=lambda e: e["date"])
    return data


def check_banned(text, label):
    for char, name in BANNED.items():
        if char in text:
            line = text[: text.index(char)].count("\n") + 1
            fail("%s 第 %d 行含有 %s，請改用逗號或括號" % (label, line, name))


def main():
    data = load_data()

    try:
        template = TEMPLATE.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail("找不到 " + str(TEMPLATE))

    if PLACEHOLDER not in template:
        fail("template.html 裡找不到佔位符 " + PLACEHOLDER)

    check_banned(template, "template.html")
    check_banned(DATA.read_text(encoding="utf-8"), "data.json")

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # 避免 JSON 內容提前結束 script 區塊，或帶入 JS 不合法的行分隔字元
    payload = payload.replace("</", "<\\/")
    payload = payload.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")

    html = template.replace(PLACEHOLDER, payload)
    check_banned(html, "dashboard.html")

    OUTPUT.write_text(html, encoding="utf-8")
    # Cloudflare Pages 要有 index.html 當首頁，內容跟 dashboard.html 一樣
    INDEX.write_text(html, encoding="utf-8")

    entries = data["entries"]
    weighed = [e for e in entries if e.get("weight_kg") is not None]
    print("已產生 " + OUTPUT.name + " 與 " + INDEX.name)
    print(
        "  entries %d 筆，有量體重 %d 筆，phase %s，預算 %s kcal"
        % (
            len(entries),
            len(weighed),
            data["config"]["phase"],
            data["config"]["budget_kcal"],
        )
    )
    if entries:
        print("  日期範圍 " + entries[0]["date"] + " 到 " + entries[-1]["date"])
    print("  檔案大小 %d bytes" % OUTPUT.stat().st_size)
    print("  index.html %d bytes（與 dashboard.html 相同）" % INDEX.stat().st_size)


if __name__ == "__main__":
    main()
