#!/bin/zsh
# Обновляет данные и публикует их на GitHub Pages, если что-то изменилось.
# Запускается по расписанию через launchd (см. install-schedule.sh).
set -u
cd "$(dirname "$0")" || exit 1

PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
STAMP=$(date '+%Y-%m-%d %H:%M:%S')

# парсер пишет прогресс в stderr, поэтому лог общий, а не только для ошибок
# источник иногда троттлит запросы — тогда пробуем ещё раз через 3 минуты,
# чтобы не ждать полный цикл расписания
if ! python3 parser.py --delay 0.8 >/dev/null 2>>logs/parser.log; then
  echo "$STAMP  источник не ответил, повтор через 3 мин"
  sleep 180
  if ! python3 parser.py --delay 1.2 >/dev/null 2>>logs/parser.log; then
    echo "$(date '+%Y-%m-%d %H:%M:%S')  повтор тоже не удался (см. logs/parser.log)"
    exit 0   # не ошибка: попробуем в следующий цикл расписания
  fi
  echo "$(date '+%Y-%m-%d %H:%M:%S')  повтор удался"
fi

if git diff --quiet -- data/stations.json; then
  echo "$STAMP  данные без изменений, публикация не нужна"
  exit 0
fi

CHANGES=$(python3 -c "import json;print(len(json.load(open('data/stations.json'))['changes']))")
git add data/stations.json
git commit -q -m "data: снимок $STAMP (изменений: $CHANGES)"

# remote может отсутствовать (публикация не настроена) — тогда просто пишем локально
if ! git remote get-url origin >/dev/null 2>&1; then
  echo "$STAMP  данные обновлены локально, изменений статусов: $CHANGES"
  exit 0
fi

if git push -q origin main 2>>logs/push-errors.log; then
  echo "$STAMP  опубликовано, изменений статусов: $CHANGES"
else
  echo "$STAMP  push не удался (см. logs/push-errors.log)"
fi
