#!/bin/zsh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$APP_DIR/.." && pwd)"
INSTALL_MODE="${1:-}"
NAME="Blender Studio"
BUILD="$APP_DIR/dist"
BUNDLE="$BUILD/$NAME.app"
CONTENTS="$BUNDLE/Contents"
ICONSET="$BUILD/BlenderStudioIcon.iconset"
SOURCE_ICON="${BLENDER_STUDIO_ICON:-$ROOT/assets_blender/09_hero_back_top_34.png}"
DEFAULT_BLEND="${BLENDER_STUDIO_DEFAULT_BLEND:-}"

rm -rf "$BUNDLE" "$ICONSET"
mkdir -p "$CONTENTS/MacOS" "$CONTENTS/Resources" "$ICONSET"
/usr/bin/swiftc "$APP_DIR/macos/BlenderStudioApp.swift" -O -framework Cocoa -framework WebKit -o "$CONTENTS/MacOS/BlenderStudio"
/usr/bin/sed -e "s|__COMPOSE_PATH__|$APP_DIR/compose.yml|g" -e "s|__BLENDER_ROOT__|$ROOT|g" -e "s|__DEFAULT_BLEND__|$DEFAULT_BLEND|g" "$APP_DIR/macos/Info.plist" > "$CONTENTS/Info.plist"

BASE="$BUILD/BlenderStudioIcon-1024.png"
/usr/bin/sips --resampleHeightWidthMax 760 "$SOURCE_ICON" --out "$BASE" >/dev/null
/usr/bin/sips --padToHeightWidth 1024 1024 --padColor 17191E "$BASE" --out "$BASE" >/dev/null
for spec in "16 icon_16x16.png" "32 icon_16x16@2x.png" "32 icon_32x32.png" "64 icon_32x32@2x.png" "128 icon_128x128.png" "256 icon_128x128@2x.png" "256 icon_256x256.png" "512 icon_256x256@2x.png" "512 icon_512x512.png" "1024 icon_512x512@2x.png"; do
  set -- $=spec; /usr/bin/sips -z "$1" "$1" "$BASE" --out "$ICONSET/$2" >/dev/null
done
/usr/bin/iconutil -c icns "$ICONSET" -o "$CONTENTS/Resources/BlenderStudioIcon.icns"
/usr/bin/codesign --force --deep --sign - "$BUNDLE"

if [[ "$INSTALL_MODE" == "--install" ]]; then
  rm -rf "/Applications/$NAME.app"
  /usr/bin/ditto "$BUNDLE" "/Applications/$NAME.app"
  /usr/bin/codesign --verify --deep --strict "/Applications/$NAME.app"
  echo "Installé: /Applications/$NAME.app"
else
  echo "Construit: $BUNDLE"
fi
