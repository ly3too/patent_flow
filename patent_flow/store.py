"""Thin wrapper around lark-cli for all Feishu read/write operations.

Command surface verified against the installed lark-cli (1.0.53) during the
first live case-init debug run: `base +query` / `+record-create` /
`+record-update` and `im +send --receive-id` do not exist in this CLI
version — the real subcommands are `+record-list` (filter-json), `+record-
upsert` (create when `--record-id` is omitted, update when it's given), and
`+messages-send --chat-id`.
"""
import json
import subprocess
from dataclasses import dataclass


def _run(args: list[str]) -> str:
    result = subprocess.run(
        ["lark-cli"] + args,
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


@dataclass
class CaseRecord:
    case_no: str
    chat_id: str
    doc_token: str
    current_node: str
    status: str


def _rows_from_record_list(payload: str) -> list[dict]:
    """`+record-list`/`+record-search --format json` return a columnar
    envelope (`data.fields` + `data.data` row arrays + `data.record_id_list`),
    not a list of `{record_id, fields}` objects. Zip them back into one dict
    per row, keyed by field name, with the record id under `_record_id`."""
    data = json.loads(payload)["data"]
    field_names = data["fields"]
    record_ids = data.get("record_id_list", [])
    rows = []
    for i, row in enumerate(data.get("data", [])):
        fields = dict(zip(field_names, row))
        if i < len(record_ids):
            fields["_record_id"] = record_ids[i]
        rows.append(fields)
    return rows


class BitableStore:
    def __init__(self, app_token: str, main_table_id: str, events_table_id: str):
        self.app_token = app_token
        self.main_table_id = main_table_id
        self.events_table_id = events_table_id

    def get_case(self, case_no: str) -> dict:
        """Returns the record's fields plus its bitable `_record_id`, needed
        by anything that will later call `update_case()`/`transition()`."""
        out = _run([
            "base", "+record-list",
            "--base-token", self.app_token,
            "--table-id", self.main_table_id,
            "--filter-json", json.dumps({"logic": "and", "conditions": [["案号", "==", case_no]]}, ensure_ascii=False),
            "--format", "json",
        ])
        rows = _rows_from_record_list(out)
        if not rows:
            raise KeyError(f"Case not found: {case_no}")
        return rows[0]

    def get_case_by_chat_id(self, chat_id: str) -> dict:
        """一案一群：群 ID 反查案件（design.md §6.1）。"""
        out = _run([
            "base", "+record-list",
            "--base-token", self.app_token,
            "--table-id", self.main_table_id,
            "--filter-json", json.dumps({"logic": "and", "conditions": [["群ID", "==", chat_id]]}, ensure_ascii=False),
            "--format", "json",
        ])
        rows = _rows_from_record_list(out)
        if not rows:
            raise KeyError(f"No case found for chat_id: {chat_id}")
        return rows[0]

    def list_cases_by_node(self, node: str) -> list[dict]:
        """Used by cron scans (S6/S8) to find every case currently sitting
        on a given state-machine node."""
        out = _run([
            "base", "+record-list",
            "--base-token", self.app_token,
            "--table-id", self.main_table_id,
            "--filter-json", json.dumps({"logic": "and", "conditions": [["当前节点", "==", node]]}, ensure_ascii=False),
            "--format", "json",
        ])
        return _rows_from_record_list(out)

    def update_case(self, record_id: str, fields: dict) -> None:
        _run([
            "base", "+record-upsert",
            "--base-token", self.app_token,
            "--table-id", self.main_table_id,
            "--record-id", record_id,
            "--json", json.dumps(fields, ensure_ascii=False),
        ])

    def append_event(self, case_no: str, source: str, event_type: str,
                     summary: str, detail_url: str = "") -> None:
        _run([
            "base", "+record-upsert",
            "--base-token", self.app_token,
            "--table-id", self.events_table_id,
            "--json", json.dumps({
                "案号": case_no,
                "来源": source,
                "事件类型": event_type,
                "摘要": summary,
                "详情链接": detail_url,
            }, ensure_ascii=False),
        ])


class LarkIM:
    def send(self, chat_id: str, text: str) -> None:
        _run([
            "im", "+messages-send",
            "--chat-id", chat_id,
            "--text", text,
        ])

    def update_chat(self, chat_id: str, name: str | None = None,
                    announcement: str | None = None) -> None:
        """`announcement` needs `im:chat.announcement:read/write` scopes and
        a block-diff body (same shape as `docs +update`) — the CLI has no
        shortcut for it yet, so it's out of scope for this thin wrapper.
        Name/description go through `+chat-update`."""
        if name:
            _run(["im", "+chat-update", "--chat-id", chat_id, "--name", name])


class LarkDoc:
    def update_block(self, doc_token: str, block_id: str, content: str) -> None:
        _run([
            "docs", "+update",
            "--api-version", "v2",
            "--doc", doc_token,
            "--command", "block_replace",
            "--block-id", block_id,
            "--content", content,
        ])
