#!/usr/bin/env bash
# Create .env from .env.example if missing, replacing "change_me" placeholders with random
# secrets and setting AIRFLOW_UID to the current user. Idempotent: never overwrites .env.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  echo "[init_env] .env exists — leaving it unchanged"
  exit 0
fi

# Linux: container uid must match the host uid for bind mounts. Windows/macOS Docker Desktop
# maps ownership itself, and Git Bash's `id -u` is not a real uid -> use the image default.
case "$(uname -s)" in
  Linux*) HOST_UID=$(id -u) ;;
  *) HOST_UID=50000 ;;
esac
id() { echo "$HOST_UID"; }

rand() { python3 -c 'import secrets; print(secrets.token_urlsafe(24))'; }
fernet() { python3 -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'; }

while IFS= read -r line; do
  line=${line%$'\r'}  # tolerate CRLF checkouts (Windows)
  case "$line" in
    AIRFLOW_UID=*) echo "AIRFLOW_UID=$(id -u)" ;;
    *=change_me_fernet) echo "${line%%=*}=$(fernet)" ;;
    *=change_me) echo "${line%%=*}=$(rand)" ;;
    *) echo "$line" ;;
  esac
done < .env.example > .env
chmod 600 .env
echo "[init_env] .env created with random secrets (AIRFLOW_UID=$(id -u))"
