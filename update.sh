#!/bin/zsh
# Refreshes the data and publishes it to GitHub Pages if anything changed.
# Run on a schedule by launchd (see install-schedule.sh).
set -u
cd "$(dirname "$0")" || exit 1

PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
STAMP=$(date '+%Y-%m-%d %H:%M:%S')

# the parser writes progress to stderr, so this log holds output, not just errors;
# the source throttles now and then, so retry after 3 minutes instead of
# waiting out the full schedule interval
if ! python3 parser.py --delay 0.8 >/dev/null 2>>logs/parser.log; then
  echo "$STAMP  source did not answer, retrying in 3 min"
  sleep 180
  if ! python3 parser.py --delay 1.2 >/dev/null 2>>logs/parser.log; then
    echo "$(date '+%Y-%m-%d %H:%M:%S')  retry failed too (see logs/parser.log)"
    exit 0   # not a failure: the next scheduled cycle will try again
  fi
  echo "$(date '+%Y-%m-%d %H:%M:%S')  retry succeeded"
fi

if git diff --quiet -- data/stations.json; then
  echo "$STAMP  data unchanged, nothing to publish"
  exit 0
fi

CHANGES=$(python3 -c "import json;print(len(json.load(open('data/stations.json'))['changes']))")
git add data/stations.json
git commit -q -m "data: snapshot $STAMP ($CHANGES status changes)"

# there may be no remote (publishing not set up) — then just keep the data local
if ! git remote get-url origin >/dev/null 2>&1; then
  echo "$STAMP  updated locally, status changes: $CHANGES"
  exit 0
fi

if git push -q origin main 2>>logs/push-errors.log; then
  echo "$STAMP  published, status changes: $CHANGES"
else
  echo "$STAMP  push failed (see logs/push-errors.log)"
fi
