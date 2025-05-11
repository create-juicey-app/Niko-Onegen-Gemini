#!/usr/bin/env bash
# Build single‐file EXE including resource dirs
pyinstaller \
  --noconfirm \
  --onefile \
  --add-data "res:res" \
  --add-data "characters:characters" \
  main.py
