#!/usr/bin/env bash
# Host prerequisite check for GridPulse (Linux). Prints Item | Found | Required | Status.
# Exit code 1 if anything is MISSING or needs an UPGRADE.
set -uo pipefail

FAIL=0
ROWS=()

# version_ge A B -> true if A >= B (dotted numeric)
version_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" = "$2" ]; }
ver() { grep -oE '[0-9]+(\.[0-9]+)+' <<<"$1" | head -1; }

row() {  # item found required status
  ROWS+=("$(printf '| %-22s | %-28s | %-14s | %-7s |' "$1" "$2" "$3" "$4")")
  [[ "$4" == "MISSING" || "$4" == "UPGRADE" ]] && FAIL=1
}

check_tool() {  # name command min [optional-note]
  local name=$1 cmd=$2 min=$3 out v
  if out=$(eval "$cmd" 2>/dev/null) && [[ -n "$out" ]]; then
    v=$(ver "$out")
    if [[ "$min" == "any" ]] || version_ge "$v" "$min"; then row "$name" "$v" ">= $min" "OK"
    else row "$name" "$v" ">= $min" "UPGRADE"; fi
  else
    if [[ "${4:-}" == "optional" ]]; then row "$name" "not found" "optional" "SKIP"
    else row "$name" "not found" ">= $min" "MISSING"; fi
  fi
}

# --- host ---
. /etc/os-release
row "OS" "${PRETTY_NAME}" "Linux x86_64" "$([[ $(uname -m) == x86_64 ]] && echo OK || echo UPGRADE)"
CORES=$(nproc)
row "CPU cores" "$CORES" ">= 4" "$([[ $CORES -ge 4 ]] && echo OK || echo UPGRADE)"
RAM_GB=$(awk '/MemTotal/{printf "%.1f", $2/1048576}' /proc/meminfo)
AVAIL_GB=$(awk '/MemAvailable/{printf "%.1f", $2/1048576}' /proc/meminfo)
row "RAM total (GB)" "$RAM_GB" ">= 8 (LITE)" "$(awk -v r="$RAM_GB" 'BEGIN{print (r>=8)?"OK":"UPGRADE"}')"
row "RAM available (GB)" "$AVAIL_GB" ">= 5" "$(awk -v r="$AVAIL_GB" 'BEGIN{print (r>=5)?"OK":"WARN"}')"
DISK_GB=$(df -BG --output=avail . | tail -1 | tr -dc '0-9')
row "Free disk (GB)" "$DISK_GB" ">= 20" "$([[ $DISK_GB -ge 20 ]] && echo OK || echo UPGRADE)"
VIRT=$(grep -cE 'vmx|svm' /proc/cpuinfo)
row "Virtualization" "$([[ $VIRT -gt 0 ]] && echo enabled || echo disabled)" "enabled" "$([[ $VIRT -gt 0 ]] && echo OK || echo MISSING)"

# --- tools ---
check_tool "git" "git --version" "2.30"
check_tool "Docker (client)" "docker --version" "24.0"
check_tool "Docker Compose" "docker compose version --short" "2.20"
check_tool "Python 3" "python3 --version" "3.11"
check_tool "python3 venv" "python3 -m venv --help >/dev/null && python3 --version" "3.11"
check_tool "pip (python3 -m pip)" "python3 -m pip --version" "any" optional
check_tool "Java (JDK)" "java -version 2>&1" "11" optional
check_tool "make" "make --version" "4.0"
check_tool "curl" "curl --version" "7.0"

# Docker daemon reachable without sudo?
if docker info >/dev/null 2>&1; then row "Docker daemon access" "ok" "no sudo" "OK"
else row "Docker daemon access" "denied" "no sudo" "MISSING"; fi

for p in 8080 8088 5433; do
  if ss -ltn 2>/dev/null | grep -q ":$p\b"; then
    owner=$(docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -E ":$p->" | awk '{print $1}')
    if [[ "$owner" == gridpulse-* ]]; then row "Port $p" "used by $owner" "free/ours" "OK"
    else row "Port $p" "in use" "free" "WARN"; fi
  else row "Port $p" "free" "free" "OK"; fi
done

echo "GridPulse system check — $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "Note: Java is optional (Spark dropped, ADR-002)."
printf '| %-22s | %-28s | %-14s | %-7s |\n' "Item" "Found" "Required" "Status"
printf '|%s|%s|%s|%s|\n' "------------------------" "------------------------------" "----------------" "---------"
printf '%s\n' "${ROWS[@]}"
if [[ $FAIL -eq 0 ]]; then echo "RESULT: OK"; else echo "RESULT: FIX ITEMS MARKED MISSING/UPGRADE"; fi
exit $FAIL
