#!/usr/bin/env python3
import subprocess
import sys

result = subprocess.run([sys.executable, "scripts/generate.py"])
if result.returncode != 0:
    print("Static site generation failed.", file=sys.stderr)
    sys.exit(result.returncode)

print("Cloudflare build output is ready in ./dist")
