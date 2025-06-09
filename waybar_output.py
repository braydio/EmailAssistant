#!/usr/bin/env python3
import json
import os
import time
import sys

status_file = os.path.expanduser("~/.cache/email_status.json")
spinner = [
    "(╯°□°）╯︵ ┻━┻",
    "ヽ(`Д´)ﾉ",
    "┻━┻ ︵ヽ(`Д´)ﾉ︵﻿ ┻━┻",
    "（╯°□°）╯︵( .o.)",
    "┬─┬ ノ( ゜-゜ノ)",
    "( •_•)>⌐■-■",
    "(⌐■_■)"
]

default_icon = "󰻧"

def main():
    i = 0
    while True:
        try:
            with open(status_file, "r") as f:
                data = json.load(f)
        except:
            data = {"text": f"{default_icon} ?", "tooltip": "Waiting for status"}

        processing = data.get("processing", False)

        if processing:
            icon = f"{spinner[i % len(spinner)]} "

            output = {
                "text": icon,
                "tooltip": data.get("tooltip", "Processing emails")
            }
            print(json.dumps(output))
            sys.stdout.flush()
            time.sleep(0.05)
            i += 1
        else:
            # Show whatever the last real status was
            output = {
                "text": data.get("text", f"{default_icon} ?"),
                "tooltip": data.get("tooltip", ""),
                "class": data.get("class", "idle")
            }
            print(json.dumps(output))
            sys.stdout.flush()
            time.sleep(5)

if __name__ == "__main__":
    main()
