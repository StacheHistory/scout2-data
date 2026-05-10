#!/usr/bin/env python3
"""
Scout-2 Notification Script — Investing with SPACE System
Checks for immediate alerts and shows Windows desktop notifications.
Also writes email-ready summary to data/scout2_email_alert.txt
Run after scout2_phase2.py
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR   = Path("data")
ALERTS_FILE = DATA_DIR / "scout2_alerts.json"
EMAIL_FILE  = DATA_DIR / "scout2_email_alert.txt"


def show_windows_notification(title: str, message: str):
    """Show a Windows 10/11 toast notification using PowerShell."""
    # Escape single quotes for PowerShell
    title   = title.replace("'", "`'")
    message = message.replace("'", "`'")

    ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.Visible = $true
$notify.BalloonTipTitle = '{title}'
$notify.BalloonTipText = '{message}'
$notify.BalloonTipIcon = 'Info'
$notify.ShowBalloonTip(8000)
Start-Sleep -Seconds 9
$notify.Dispose()
"""
    try:
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"  [WARN] Notification failed: {e}", file=sys.stderr)


def main():
    if not ALERTS_FILE.exists():
        print("  [SKIP] No alerts file found — skipping notifications", file=sys.stderr)
        return

    try:
        data      = json.loads(ALERTS_FILE.read_text(encoding="utf-8"))
        immediate = data.get("immediate", [])
        same_day  = data.get("same_day",  [])
        meta      = data.get("meta", {})
    except Exception as e:
        print(f"  [ERROR] Could not read alerts: {e}", file=sys.stderr)
        return

    total_immediate = len(immediate)
    total_same_day  = len(same_day)

    print(f"  Immediate alerts: {total_immediate}", file=sys.stderr)
    print(f"  Same-day alerts:  {total_same_day}", file=sys.stderr)

    # ── Desktop notification for immediate alerts ──────────────────
    if total_immediate > 0:
        top = immediate[0]
        companies = ", ".join(top.get("company", ["Unknown"])[:2])
        headline  = top.get("headline", "")[:80]

        title   = f"🚨 Scout-2: {total_immediate} IMMEDIATE Alert(s)"
        message = f"{companies}: {headline}"
        show_windows_notification(title, message)
        print(f"  [NOTIFY] Immediate alert notification sent", file=sys.stderr)

    elif total_same_day > 0:
        top = same_day[0]
        companies = ", ".join(top.get("company", ["Unknown"])[:2])

        title   = f"⚡ Scout-2: {total_same_day} Same-Day Alert(s)"
        message = f"{companies}: {top.get('headline','')[:80]}"
        show_windows_notification(title, message)
        print(f"  [NOTIFY] Same-day alert notification sent", file=sys.stderr)

    else:
        print(f"  [INFO] No immediate alerts — no notification needed", file=sys.stderr)


if __name__ == "__main__":
    main()
