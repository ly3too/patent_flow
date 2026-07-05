#!/usr/bin/env bash
# Idempotent bootstrap of the patent_flow Feishu knowledge-base infra:
#
#   patent_flow (wiki space, IS the root)
#   ├── 专利流程管理.bitable  (案件主表 + 事件流水, with the full field schema)
#   ├── templates            (docx node, parent-only placeholder)
#   └── cases                (docx node, parent-only placeholder)
#
# Safe to re-run: every step looks up existing resources BY NAME first and
# only creates what's missing, so running this against an already-bootstrapped
# tenant is a no-op except for filling in any gaps. Requires `lark-cli auth
# login` (user identity) to already be done — see README.md.
#
# Usage: scripts/setup_feishu_infra.sh [output_env_file]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-$ROOT/.env.patent_flow}"
SPACE_NAME="${PATENT_FLOW_SPACE_NAME:-patent_flow}"
BASE_NAME="${PATENT_FLOW_BASE_NAME:-专利流程管理}"

log() { echo "==> $*" >&2; }

require_user_auth() {
  local status
  status="$(lark-cli auth status --json 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)['identities']['user']['status'])" 2>/dev/null || echo missing)"
  if [[ "$status" != "ready" ]]; then
    echo "错误：lark-cli 用户身份未就绪（当前状态：$status）。" >&2
    echo "先运行：lark-cli auth login --domain base,contact,docs,drive,im,wiki" >&2
    exit 1
  fi
}

# --- 1. wiki space -----------------------------------------------------------

resolve_space() {
  local existing
  existing="$(lark-cli wiki +space-list --as user --page-all --format json 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
items = d.get('data', {}).get('items') or d.get('data', {}).get('spaces') or []
for s in items:
    if s.get('name') == '$SPACE_NAME':
        print(s['space_id'])
        break
")"
  if [[ -n "$existing" ]]; then
    log "复用已有知识库空间 \"$SPACE_NAME\" (space_id=$existing)"
    echo "$existing"
    return
  fi
  log "未找到知识库空间 \"$SPACE_NAME\"，创建中..."
  lark-cli wiki +space-create --as user --name "$SPACE_NAME" \
    --description "专利流程管理 patent-flow-skill 唯一根空间" --format json \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['space']['space_id'])"
}

# --- 2. top-level node lookup (shared by bitable/templates/cases) ------------

find_node_by_title() {
  local space_id="$1" title="$2"
  lark-cli wiki nodes list --as user --params "{\"space_id\":\"$space_id\"}" --format json 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
for n in d['data']['items']:
    if n['title'] == '$title':
        print(n['node_token'])
        break
"
}

# --- 3. 专利流程管理.bitable + schema -----------------------------------------

resolve_bitable() {
  local space_id="$1"
  local node_token base_token
  node_token="$(find_node_by_title "$space_id" "$BASE_NAME")"
  if [[ -n "$node_token" ]]; then
    base_token="$(lark-cli wiki spaces get_node --as user --params "{\"token\":\"$node_token\"}" --format json \
      | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['node']['obj_token'])")"
    log "复用已有 bitable \"$BASE_NAME\" (base_token=$base_token)"
  else
    log "未找到 \"$BASE_NAME\"，创建 bitable 节点..."
    base_token="$(lark-cli wiki +node-create --as user --space-id "$space_id" --obj-type bitable --title "$BASE_NAME" --format json \
      | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['obj_token'])")"
  fi
  echo "$base_token"
}

find_table_by_name() {
  local base_token="$1" name="$2"
  lark-cli base +table-list --as user --base-token "$base_token" --format json 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
for t in d['data']['tables']:
    if t['name'] == '$name':
        print(t['id'])
        break
"
}

field_exists() {
  local base_token="$1" table_id="$2" name="$3"
  lark-cli base +field-list --as user --base-token "$base_token" --table-id "$table_id" --format json 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('yes' if any(f['name'] == '$name' for f in d['data']['fields']) else 'no')
"
}

create_field() {
  local base_token="$1" table_id="$2" json="$3"
  lark-cli base +field-create --as user --base-token "$base_token" --table-id "$table_id" --json "$json" --format json >/dev/null
}

ensure_field() {
  local base_token="$1" table_id="$2" name="$3" json="$4"
  if [[ "$(field_exists "$base_token" "$table_id" "$name")" == "yes" ]]; then
    return
  fi
  log "  + 字段 $name"
  create_field "$base_token" "$table_id" "$json"
}

resolve_main_table() {
  local base_token="$1"
  local table_id
  table_id="$(find_table_by_name "$base_token" "案件主表")"
  if [[ -z "$table_id" ]]; then
    log "创建表 案件主表..."
    local default_table
    default_table="$(lark-cli base +table-list --as user --base-token "$base_token" --format json | python3 -c "
import json,sys
d=json.load(sys.stdin)['data']['tables']
print(d[0]['id'] if d else '')
")"
    if [[ -n "$default_table" ]]; then
      lark-cli base +table-update --as user --base-token "$base_token" --table-id "$default_table" --name "案件主表" --format json >/dev/null
      table_id="$default_table"
    else
      table_id="$(lark-cli base +table-create --as user --base-token "$base_token" --name "案件主表" --format json \
        | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['table']['id'])")"
    fi
  fi

  ensure_field "$base_token" "$table_id" "群ID" '{"type":"text","name":"群ID"}'
  ensure_field "$base_token" "$table_id" "案件文件夹" '{"type":"text","name":"案件文件夹","style":{"type":"url"}}'
  ensure_field "$base_token" "$table_id" "案件主文档" '{"type":"text","name":"案件主文档","style":{"type":"url"}}'
  ensure_field "$base_token" "$table_id" "案件名" '{"type":"text","name":"案件名"}'
  ensure_field "$base_token" "$table_id" "IPR" '{"type":"user","name":"IPR","multiple":false}'
  ensure_field "$base_token" "$table_id" "研发" '{"type":"user","name":"研发","multiple":true}'
  ensure_field "$base_token" "$table_id" "当前节点" '{"type":"select","name":"当前节点","options":[{"name":"S1_mining"},{"name":"S2_search"},{"name":"S3_disclosure"},{"name":"S4_filing"},{"name":"S5_review"},{"name":"S6_priority_watch"},{"name":"S7_oa"},{"name":"S8_annuity"},{"name":"DONE"},{"name":"TERMINATED"}]}'
  ensure_field "$base_token" "$table_id" "当前子步骤" '{"type":"text","name":"当前子步骤"}'
  ensure_field "$base_token" "$table_id" "状态" '{"type":"select","name":"状态","options":[{"name":"running","hue":"Blue"},{"name":"waiting_human","hue":"Orange"},{"name":"blocked","hue":"Red"},{"name":"done","hue":"Green"}]}'
  ensure_field "$base_token" "$table_id" "等待对象" '{"type":"text","name":"等待对象"}'
  ensure_field "$base_token" "$table_id" "截止日期" '{"type":"text","name":"截止日期"}'
  ensure_field "$base_token" "$table_id" "下一步动作" '{"type":"text","name":"下一步动作"}'
  ensure_field "$base_token" "$table_id" "品线" '{"type":"select","name":"品线","options":[{"name":"家庭影音"},{"name":"厨电"},{"name":"家居"},{"name":"测试"}]}'
  ensure_field "$base_token" "$table_id" "申请日" '{"type":"text","name":"申请日"}'
  ensure_field "$base_token" "$table_id" "优先权到期日" '{"type":"text","name":"优先权到期日"}'
  ensure_field "$base_token" "$table_id" "年费到期日" '{"type":"text","name":"年费到期日"}'

  echo "$table_id"
}

resolve_events_table() {
  local base_token="$1"
  local table_id
  table_id="$(find_table_by_name "$base_token" "事件流水")"
  if [[ -z "$table_id" ]]; then
    log "创建表 事件流水..."
    table_id="$(lark-cli base +table-create --as user --base-token "$base_token" --name "事件流水" --fields '[
      {"type":"text","name":"案号"},
      {"type":"created_at","name":"时间","style":{"format":"yyyy-MM-dd HH:mm"}},
      {"type":"select","name":"来源","options":[{"name":"agent"},{"name":"ipr"},{"name":"pm"},{"name":"system"}]},
      {"type":"text","name":"事件类型"},
      {"type":"text","name":"摘要"},
      {"type":"text","name":"详情链接","style":{"type":"url"}}
    ]' --format json | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['table']['id'])")"
  fi
  echo "$table_id"
}

# --- 4. templates / cases placeholder nodes ----------------------------------

resolve_placeholder_node() {
  local space_id="$1" title="$2"
  local token
  token="$(find_node_by_title "$space_id" "$title")"
  if [[ -n "$token" ]]; then
    log "复用已有节点 \"$title\" ($token)"
    echo "$token"
    return
  fi
  log "创建占位节点 \"$title\"..."
  lark-cli wiki +node-create --as user --space-id "$space_id" --obj-type docx --title "$title" --format json \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['node_token'])"
}

# --- main ---------------------------------------------------------------------

main() {
  require_user_auth

  local space_id base_token main_table events_table templates_token cases_token

  log "解析知识库空间..."
  space_id="$(resolve_space)"

  log "解析 bitable..."
  base_token="$(resolve_bitable "$space_id")"

  log "解析 案件主表 及字段..."
  main_table="$(resolve_main_table "$base_token")"

  log "解析 事件流水 表..."
  events_table="$(resolve_events_table "$base_token")"

  log "解析 templates 占位节点..."
  templates_token="$(resolve_placeholder_node "$space_id" "templates")"

  log "解析 cases 占位节点..."
  cases_token="$(resolve_placeholder_node "$space_id" "cases")"

  cat > "$ENV_FILE" <<EOF
# Generated by scripts/setup_feishu_infra.sh — safe to re-run, will be overwritten.
export PATENT_FLOW_ROOT_TOKEN="$space_id"
export LEDGER_APP_TOKEN="$base_token"
export LEDGER_MAIN_TABLE="$main_table"
export LEDGER_EVENTS_TABLE="$events_table"
export PATENT_FLOW_TEMPLATES_NODE="$templates_token"
export PATENT_FLOW_CASES_NODE="$cases_token"
EOF

  log "完成。资源 token 已写入 $ENV_FILE"
  echo
  cat "$ENV_FILE"
}

main
