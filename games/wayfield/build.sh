#!/bin/sh
# Assembles the game from parts/ into two files:
#   wayfield.html  page body only (the form the Artifact host wraps)
#   index.html     a complete standalone page to open in any browser
set -e
cd "$(dirname "$0")"
P=parts
{
  cat "$P/head.html"
  printf '<style>\n'; cat "$P/style.css"; printf '</style>\n'
  cat "$P/body.html"
  printf '<script>\n"use strict";\n(() => {\n'
  for f in core net gen sim render ui; do cat "$P/$f.js"; printf '\n'; done
  printf '})();\n</script>\n'
} > wayfield.html
{
  printf '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
  cat "$P/head.html"
  printf '<style>\n'; cat "$P/style.css"; printf '</style>\n</head>\n<body>\n'
  sed -n '/^<div id="app">/,$p' wayfield.html
  printf '</body>\n</html>\n'
} > index.html
echo "built wayfield.html and index.html ($(wc -c < index.html) bytes)"
