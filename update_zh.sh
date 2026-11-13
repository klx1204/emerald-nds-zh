#!/usr/bin/env bash
# 跟随上游重新生成 Emerald NDS 中文补丁。
#
#   ./update_zh.sh              # 上游最新 Release
#   ./update_zh.sh v2.1         # 指定上游 tag
#
# 需要：
#   - 干净的黑2 dump（默认 roms/black2.nds，可用 BLACK2_ROM 覆盖）
#   - gh 已登录（下载上游 bps）
#   - .venv（uv venv && uv pip install ndspy pillow numpy）
#
# 输出：
#   release/emerald-nds-zh_<version>_full.bps   原版黑2 -> 中文
#   release/emerald-nds-zh_<version>_inc.bps   上游 patched -> 中文
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${1:-latest}"
BLACK2_ROM="${BLACK2_ROM:-roms/black2.nds}"
PYTHON="${PYTHON:-.venv/bin/python}"
UPSTREAM_REPO="logdog2325/pokemon-ruby-sapphire-nds"
WORK="work/update"
mkdir -p "$WORK" release

if [ ! -x "$PYTHON" ]; then
  echo "找不到 $PYTHON；先运行：uv venv .venv && uv pip install ndspy pillow numpy" >&2
  exit 1
fi
if [ ! -f "$BLACK2_ROM" ]; then
  echo "找不到黑2原版：$BLACK2_ROM（用 BLACK2_ROM=/path/to/black2.nds 指定）" >&2
  exit 1
fi

# 1. 上游 bps（可用 UPSTREAM_BPS 跳过下载）
if [ -n "${UPSTREAM_BPS:-}" ]; then
  cp "$UPSTREAM_BPS" "$WORK/upstream.bps"
else
  echo "下载上游 Emerald bps（$VERSION）..."
  if [ "$VERSION" = "latest" ]; then
    gh release download --repo "$UPSTREAM_REPO" --pattern '*Emerald*.bps' --dir "$WORK" --clobber
  else
    gh release download "$VERSION" --repo "$UPSTREAM_REPO" --pattern '*Emerald*.bps' --dir "$WORK" --clobber
  fi
  mv "$WORK"/*Emerald*.bps "$WORK/upstream.bps"
fi
if [ "$VERSION" = "latest" ]; then
  VERSION="$(gh release view --repo "$UPSTREAM_REPO" --json tagName --jq .tagName)"
fi

# 2. 应用到原版黑2
echo "应用上游补丁..."
"$PYTHON" tools/vendor/bps.py apply "$BLACK2_ROM" "$WORK/upstream.bps" "$WORK/patched.nds"

# 3. 替换文本和字体（保持 512 MB）
echo "构建中文 ROM..."
"$PYTHON" tools/build_zh.py \
  --patched "$WORK/patched.nds" \
  --data zh_data \
  --font0 zh_data/font/font0.nftr \
  --font1 zh_data/font/font1.nftr \
  --font2 zh_data/font/font2.nftr \
  --out "$WORK/zh.nds"

# 4. 两个补丁
echo "生成 BPS..."
"$PYTHON" tools/vendor/bps.py make "$BLACK2_ROM" "$WORK/zh.nds" "release/emerald-nds-zh_${VERSION}_full.bps"
"$PYTHON" tools/vendor/bps.py make "$WORK/patched.nds" "$WORK/zh.nds" "release/emerald-nds-zh_${VERSION}_inc.bps"

# 5. 校验
echo "校验..."
( cd release && shasum -a 256 "emerald-nds-zh_${VERSION}_full.bps" "emerald-nds-zh_${VERSION}_inc.bps" | tee SHA256SUMS.txt )

if [ "${PUBLISH:-0}" = "1" ]; then
  gh release create "zh-${VERSION}" release/*.bps release/SHA256SUMS.txt \
    --repo klx1204/emerald-nds-zh \
    --title "Emerald NDS 中文补丁 zh-${VERSION}" \
    --notes "对应上游 ${VERSION}。安装顺序见 README。"
fi

echo "完成：release/emerald-nds-zh_${VERSION}_{full,inc}.bps"
