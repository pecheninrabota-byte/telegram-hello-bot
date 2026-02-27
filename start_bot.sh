#!/usr/bin/env bash
set -euo pipefail

BOT_FILE="bot.py"
PID_FILE="bot.pid"
LOG_FILE="bot.log"

cd "$(dirname "$0")"

# 0) Проверим, что файл бота существует
if [[ ! -f "$BOT_FILE" ]]; then
  echo "$(date '+%F %T') | ERROR: $BOT_FILE not found in $(pwd)" >> "$LOG_FILE"
  exit 0
fi

# 1) Если есть PID — попробуем мягко остановить старый процесс
if [[ -f "$PID_FILE" ]]; then
  oldpid="$(cat "$PID_FILE" || true)"
  if [[ -n "${oldpid:-}" ]] && kill -0 "$oldpid" 2>/dev/null; then
    echo "$(date '+%F %T') | stopping old bot pid=$oldpid" >> "$LOG_FILE"
    kill "$oldpid" 2>/dev/null || true
    sleep 1
    kill -9 "$oldpid" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
fi

# 2) Защита от дубля, если pid-файл потерялся, а процесс жив
# Ищем bot.py среди python-процессов; если нашли — гасим
pids="$(pgrep -f "python.*${BOT_FILE}" || true)"
if [[ -n "${pids:-}" ]]; then
  echo "$(date '+%F %T') | found running bot pids=${pids}. stopping..." >> "$LOG_FILE"
  kill ${pids} 2>/dev/null || true
  sleep 1
  kill -9 ${pids} 2>/dev/null || true
fi

# 3) Запуск в фоне, чтобы postStartCommand НЕ зависал
# setsid + nohup => процесс отвязан от терминала
echo "$(date '+%F %T') | starting bot..." >> "$LOG_FILE"
nohup setsid python -u "$BOT_FILE" >> "$LOG_FILE" 2>&1 < /dev/null &
newpid=$!
echo "$newpid" > "$PID_FILE"
echo "$(date '+%F %T') | started bot pid=$newpid" >> "$LOG_FILE"

exit 0