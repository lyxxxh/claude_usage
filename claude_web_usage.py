#!/usr/bin/env python3
"""
查询多个 claude.ai 账号的限额，一眼看出哪个账号最佳
"""

import os, sys, json, urllib.request, urllib.error, concurrent.futures
from pathlib import Path
from datetime import datetime, timezone

CONFIG_FILE = Path(__file__).parent / "config.json"

# ── 颜色 ──────────────────────────────────────────────────────────────────────
R="\033[0m"; B="\033[1m"
CY="\033[36m"; GR="\033[32m"; YL="\033[33m"
RD="\033[31m"; GY="\033[90m"; WH="\033[97m"; MG="\033[35m"
def c(t, col): return f"{col}{t}{R}"

# ── API ───────────────────────────────────────────────────────────────────────
def fetch_usage(account: dict) -> dict:
    """返回 {"name":..., "data":..., "error":...}"""
    name = account["name"]
    org  = account.get("org_id", "")
    sk   = account.get("session_key", "")

    if not sk:
        return {"name": name, "data": None, "error": "未配置 session_key"}

    cookie = f"sessionKey={sk}; lastActiveOrg={org}"

    try:
        req = urllib.request.Request(
            f"https://claude.ai/api/organizations/{org}/usage",
            headers={
                "Cookie": cookie,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "anthropic-client-platform": "web_claude_ai",
                "anthropic-client-version": "1.0.0",
                "Referer": "https://claude.ai/settings/usage",
            }
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read()
            if body[:1] == b"<":
                return {"name": name, "data": None, "error": "CF拦截，需重新抓包"}
            return {"name": name, "data": json.loads(body), "error": None}
    except urllib.error.HTTPError as e:
        body = e.read()
        if body[:1] == b"<":
            return {"name": name, "data": None, "error": "CF拦截，需重新抓包"}
        msg = "session_key 已过期" if e.code == 403 else f"HTTP {e.code}"
        return {"name": name, "data": None, "error": msg}
    except Exception as e:
        return {"name": name, "data": None, "error": str(e)}

# ── 格式化 ────────────────────────────────────────────────────────────────────
BAR_W = 20

def bar(pct: float) -> str:
    pct    = min(pct or 0.0, 100.0)
    filled = int(pct / 100 * BAR_W)
    col    = GR if pct < 60 else (YL if pct < 90 else RD)
    return f"{col}{'█'*filled}{R}{GY}{'░'*(BAR_W-filled)}{R}"

def fmt_pct(pct: float) -> str:
    col = GR if pct < 60 else (YL if pct < 90 else RD)
    return c(f"{pct:5.0f}%", col)

RESET_W = 9  # 固定视觉宽度

def _vlen(s: str) -> int:
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in ('W','F') else 1 for c in s)

def fmt_reset(iso: str | None) -> str:
    if not iso:
        return " " * RESET_W
    dt   = datetime.fromisoformat(iso)
    secs = int((dt - datetime.now(timezone.utc)).total_seconds())
    if secs <= 0:
        raw, col = "重置中", GR
    else:
        h, rem = divmod(secs, 3600)
        m = rem // 60
        if h >= 24:
            d = h // 24
            raw, col = f"{d}天{h%24:02d}h后", YL
        else:
            raw, col = f"{h:2d}h{m:02d}m后", CY if h >= 1 else RD
    return c(raw, col) + " " * max(0, RESET_W - _vlen(raw))

def score(data: dict | None) -> float:
    """越低越好（0=最佳）。5小时即将重置则折算惩罚"""
    if not data:
        return 999
    fh_info = data.get("five_hour") or {}
    sd_info = data.get("seven_day") or {}
    fh_pct  = fh_info.get("utilization") or 0.0
    sd_pct  = sd_info.get("utilization") or 0.0
    fh_reset = fh_info.get("resets_at")

    # 5小时即将重置：按剩余时间比例折算惩罚
    if fh_pct >= 90 and fh_reset:
        secs = (datetime.fromisoformat(fh_reset) - datetime.now(timezone.utc)).total_seconds()
        if 0 < secs <= 1800:          # 30 分钟内重置
            fh_pct = fh_pct * (secs / 1800)
        elif secs <= 0:
            fh_pct = 0.0

    return fh_pct * 2 + sd_pct

# ── 主流程 ────────────────────────────────────────────────────────────────────
def main():
    if not CONFIG_FILE.exists():
        print(c("未找到配置文件: " + str(CONFIG_FILE), RD))
        print(c("请将 config.example.json 改名为 config.json 并填入账号信息", YL))
        sys.exit(1)

    with open(CONFIG_FILE, encoding="utf-8") as f:
        cfg = json.load(f)

    # 代理配置（可在 config.json 中设置 proxy 字段覆盖）
    proxy = cfg.get("proxy", "http://127.0.0.1:9999")
    os.environ["https_proxy"] = proxy
    os.environ["http_proxy"]  = proxy
    os.environ["HTTPS_PROXY"] = proxy
    os.environ["HTTP_PROXY"]  = proxy

    accounts = cfg.get("accounts", [])
    if not accounts:
        print(c("配置文件中没有 accounts", RD))
        sys.exit(1)

    print(f"\n{B}{CY}{'─'*72}{R}")
    print(f"  {B}{WH}Claude.ai 多账号限额对比{R}   {GY}{datetime.now().strftime('%H:%M:%S')}{R}")
    print(f"{B}{CY}{'─'*72}{R}\n")

    # 并发查询所有账号
    print(c(f"  查询 {len(accounts)} 个账号中...", GY))
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(accounts)) as ex:
        results = list(ex.map(fetch_usage, accounts))

    # ── 表头 ─────────────────────────────────────────────────────────────────
    col_name = 8
    print(f"\n  {B}{'账号':<{col_name}}  {'5小时限额':<{BAR_W+12}}  {'7天限额':<{BAR_W+12}}{R}")
    print(f"  {GY}{'─'*68}{R}")

    for res in results:
        name = res["name"]
        data = res["data"]
        err  = res["error"]

        if err:
            print(f"  {GY}{name:<{col_name}}{R}  {RD}{err}{R}")
            continue

        fh = data.get("five_hour") or {}
        sd = data.get("seven_day") or {}

        fh_str = f"{bar(fh.get('utilization') or 0)} {fmt_pct(fh.get('utilization') or 0)} {fmt_reset(fh.get('resets_at'))}"
        sd_str = f"{bar(sd.get('utilization') or 0)} {fmt_pct(sd.get('utilization') or 0)} {fmt_reset(sd.get('resets_at'))}"

        print(f"  {GY}{name:<{col_name}}{R}  {fh_str}  {sd_str}")

    print()


if __name__ == "__main__":
    main()
