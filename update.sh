#!/bin/zsh
# Обновляет данные и публикует их на GitHub Pages, если что-то изменилось.
# Запускается по расписанию через launchd (см. install-schedule.sh).
set -u
cd "$(dirname "$0")" || exit 1

PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
STAMP=$(date '+%Y-%m-%d %H:%M:%S')

# парсер пишет прогресс в stderr, поэтому лог общий, а не только для ошибок
if ! python3 parser.py --delay 0.8 >/dev/null 2>>logs/parser.log; then
  echo "$STAMP  парсер не смог получить данные (см. logs/parser.log)"
  exit 0   # не ошибка: источник троттлит, попробуем в следующий раз
fi

if git diff --quiet -- data/stations.json; then
  echo "$STAMP  данные без изменений, публикация не нужна"
  exit 0
fi

CHANGES=$(python3 -c "import json;print(len(json.load(open('data/stations.json'))['changes']))")
git add data/stations.json
git commit -q -m "data: снимок $STAMP (изменений: $CHANGES)"
if git push -q origin main 2>>logs/push-errors.log; then
  echo "$STAMP  опубликовано, изменений статусов: $CHANGES"
else
  echo "$STAMP  push не удался (см. logs/push-errors.log)"
fi
