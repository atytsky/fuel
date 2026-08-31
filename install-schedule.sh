#!/bin/zsh
# Ставит (или обновляет) расписание обновления данных: каждые 30 минут.
# Снять: launchctl bootout gui/$(id -u)/dev.andy.fuel-update
#        rm ~/Library/LaunchAgents/dev.andy.fuel-update.plist
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL=dev.andy.fuel-update
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
INTERVAL=${1:-1800}   # секунды, по умолчанию 30 минут

mkdir -p "$DIR/logs" "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>$DIR/update.sh</string>
  </array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>StartInterval</key><integer>$INTERVAL</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$DIR/logs/update.log</string>
  <key>StandardErrorPath</key><string>$DIR/logs/update.log</string>
  <key>ProcessType</key><string>Background</string>
</dict>
</plist>
PL

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Расписание установлено: каждые $INTERVAL с. Логи: $DIR/logs/update.log"
launchctl print "gui/$(id -u)/$LABEL" | grep -E '^\s+(state|program|runs) ' || true
