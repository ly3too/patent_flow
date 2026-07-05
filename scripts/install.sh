#!/usr/bin/env bash
# One-click setup for patent-flow-skill: lark-cli install + Feishu app
# binding/creation + user auth + knowledge-base bootstrap + Python env +
# skill symlinks. Safe to re-run — every step checks before it acts.
#
# Prerequisites this script does NOT install for you (see README.md):
#   - Feishu (飞书) client, logged into your tenant
#   - Claude Code and/or OpenClaw
#   - Node.js >= 18 (for `npm install -g lark-cli`)
#   - A Python interpreter >= 3.10 somewhere on your machine
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

log()  { echo "==> $*"; }
warn() { echo "!!  $*" >&2; }
die()  { echo "错误：$*" >&2; exit 1; }

# --- 1. lark-cli --------------------------------------------------------------

install_lark_cli() {
  if command -v lark-cli >/dev/null 2>&1; then
    log "lark-cli 已安装 ($(lark-cli --version 2>&1 | head -1))"
    return
  fi
  command -v npm >/dev/null 2>&1 || die "没有找到 npm，请先安装 Node.js (https://nodejs.org)"
  log "安装 lark-cli..."
  npm install -g @larksuiteoapi/lark-cli
}

# --- 2. Feishu app binding/creation -------------------------------------------

setup_app_config() {
  if lark-cli config show >/dev/null 2>&1; then
    log "lark-cli 已配置飞书应用，跳过创建/绑定"
    return
  fi

  if [[ -n "${OPENCLAW_HOME:-}" || -n "${HERMES_HOME:-}" ]]; then
    log "检测到 OpenClaw/Hermes 环境。"
    echo
    echo "patent-flow-skill 需要读写你自己的云空间/知识库/群聊等个人资源，"
    echo "这要求 lark-cli 用 --identity user-default 绑定（会取得以你身份操作的权限）。"
    echo "如果不确定，选择更安全的 bot-only；但那样 wiki/drive 相关功能会不可用。"
    read -r -p "确认使用 user-default 身份绑定 OpenClaw 的飞书应用？[y/N] " reply
    if [[ "$reply" =~ ^[Yy]$ ]]; then
      lark-cli config bind --source openclaw --identity user-default
    else
      log "已跳过绑定，改为创建一个独立的飞书应用..."
      lark-cli config init --new --force-init
    fi
  else
    log "未检测到已有配置，启动创建新飞书应用向导（会打开浏览器，请按提示操作）..."
    lark-cli config init --new
  fi
}

# --- 3. user-identity OAuth ----------------------------------------------------

ensure_user_auth() {
  local status
  status="$(lark-cli auth status --json 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)['identities']['user']['status'])" 2>/dev/null || echo missing)"
  if [[ "$status" == "ready" ]]; then
    log "lark-cli 用户身份已就绪"
    return
  fi
  log "需要用户身份授权（会打开浏览器，请扫码或点击链接完成登录）..."
  lark-cli auth login --domain base,contact,docs,drive,im,wiki

  log "群公告需要单独申请权限（--domain 覆盖不到），尝试追加授权..."
  lark-cli auth login --scope "im:chat.announcement:read im:chat.announcement:write_only" || \
    warn "群公告权限申请失败——如果开发者后台还没给应用勾选这两个权限，patent-case-init 会退化用 Pin 消息代替群公告（见 README「权限检查清单」）。"
}

# --- 3.5 bot app IDs (lark-cli's own app + OpenClaw's, if different) -----------
# NOTE: must run AFTER setup_feishu_infra() — that step (over)writes
# .env.patent_flow with `>`, so anything appended before it would be wiped.

detect_bot_app_ids() {
  local lark_cli_app_id openclaw_app_id=""
  lark_cli_app_id="$(lark-cli config show 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('appId',''))" 2>/dev/null || true)"

  if [[ -f "$HOME/.openclaw/openclaw.json" ]]; then
    openclaw_app_id="$(python3 -c "
import json
try:
    with open('$HOME/.openclaw/openclaw.json') as f:
        print(json.load(f).get('channels', {}).get('feishu', {}).get('appId', ''))
except Exception:
    print('')
" 2>/dev/null)"
  fi

  {
    echo "export LARK_CLI_APP_ID=\"$lark_cli_app_id\""
    [[ -n "$openclaw_app_id" ]] && echo "export OPENCLAW_APP_ID=\"$openclaw_app_id\""
  } >> "$ROOT/.env.patent_flow"

  log "lark-cli 应用 bot: ${lark_cli_app_id:-<未配置>}"
  if [[ -n "$openclaw_app_id" ]]; then
    if [[ "$openclaw_app_id" != "$lark_cli_app_id" ]]; then
      log "OpenClaw 应用 bot: $openclaw_app_id（与 lark-cli 绑定的应用不同——建群时两个 bot 都会被邀请入群）"
    else
      log "OpenClaw 应用 bot 与 lark-cli 绑定的是同一个应用"
    fi
  fi
}

# --- 4. Feishu knowledge-base infra --------------------------------------------

setup_feishu_infra() {
  log "初始化 patent_flow 知识库（wiki 空间 + 专利流程管理.bitable + templates/cases）..."
  bash "$ROOT/scripts/setup_feishu_infra.sh" "$ROOT/.env.patent_flow"
}

# --- 5. Python environment ------------------------------------------------------

find_python() {
  local candidate
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        command -v "$candidate"
        return
      fi
    fi
  done
  return 1
}

setup_python_env() {
  local py
  if ! py="$(find_python)"; then
    die "没有找到 Python >= 3.10（系统自带的 python3 通常是旧版本）。请安装一个（如 brew install python@3.12），再重新运行本脚本。"
  fi
  log "使用 Python: $py ($("$py" --version))"
  echo "export PYTHON=\"$py\"" >> "$ROOT/.env.patent_flow"
  log "安装 patent_flow 依赖..."
  "$py" -m pip install -e "$ROOT[dev]" --quiet
}

# --- 6. skills symlinks ---------------------------------------------------------

setup_skills() {
  log "把 skills/ 软链到已安装的 Claude Code / OpenClaw..."
  bash "$ROOT/scripts/link_skills.sh"
}

# --- 7. sanity check -------------------------------------------------------------

run_tests() {
  local py
  py="$(grep '^export PYTHON=' "$ROOT/.env.patent_flow" | cut -d'"' -f2)"
  log "跑一遍测试确认环境没问题..."
  (cd "$ROOT" && "$py" -m pytest -q)
}

print_summary() {
  echo
  echo "================================================================"
  echo " 安装完成！"
  echo "================================================================"
  echo
  echo "资源 token 见 $ROOT/.env.patent_flow（tools/*.sh 和 python -m patent_flow"
  echo "都需要这些环境变量——运行前先 source 一下：source .env.patent_flow）"
  echo
  cat "$ROOT/.env.patent_flow"
  echo
  echo "下一步：在 Claude Code 或 OpenClaw 里说一句类似"
  echo '  "新建一个专利案件：<专利名称>，品线=测试，IPR=我，研发=我"'
  echo "会触发 patent-case-init 这个 skill，跑通一案一群初始化。"
  echo "================================================================"
}

main() {
  install_lark_cli
  setup_app_config
  ensure_user_auth
  setup_feishu_infra
  detect_bot_app_ids
  setup_python_env
  setup_skills
  run_tests
  print_summary
}

main
