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
    """All group-facing actions run `--as bot` — the Agent posts as the app's
    own bot identity, not by impersonating the human IPR who happens to be
    logged in (that's what `--as user` is for, and it's reserved for
    resource-creation steps like `+chat-create` that need to invite humans
    in one step)."""

    def send(self, chat_id: str, text: str) -> str:
        """Returns the sent message's `message_id`, e.g. for `pin()`."""
        out = _run([
            "im", "+messages-send",
            "--as", "bot",
            "--chat-id", chat_id,
            "--text", text,
        ])
        return json.loads(out)["data"]["message_id"]

    def pin(self, chat_id: str, message_id: str) -> None:
        _run(["im", "pins", "create", "--as", "bot", "--data", json.dumps({"message_id": message_id})])

    def update_chat(self, chat_id: str, name: str | None = None) -> None:
        if name:
            _run(["im", "+chat-update", "--as", "bot", "--chat-id", chat_id, "--name", name])

    def set_announcement(self, chat_id: str, text: str) -> None:
        """Replace the chat's 群公告 with a single text block.

        There's no lark-cli shortcut for this (verified: no schema entry
        exists for the announcement resource at all), and the *legacy*
        `GET/PATCH /open-apis/im/v1/chats/:chat_id/announcement` fails with
        `232097 Unable to operate docx type chat announcement` for chats
        whose announcement has been upgraded to the newer docx-block model
        (which appears to be the default now). The real path is the
        `docx/v1` "upgraded group announcement" API, block-based like a docx
        document — its root block token is the `chat_id` itself:
          - read:   GET    /open-apis/docx/v1/chats/:chat_id/announcement/blocks/:chat_id/children
          - clear:  DELETE /open-apis/docx/v1/chats/:chat_id/announcement/blocks/:chat_id/children/batch_delete
          - write:  POST   /open-apis/docx/v1/chats/:chat_id/announcement/blocks/:chat_id/children
        `create children` only *appends*, so clear-then-append is how you
        "replace" it. Needs `im:chat.announcement:read` +
        `im:chat.announcement:write_only` enabled for the app in the Feishu
        console — if that raises, callers should fall back to a pinned
        status message (see skills/task/patent-case-init/SKILL.md).
        """
        base = f"/open-apis/docx/v1/chats/{chat_id}/announcement/blocks/{chat_id}/children"

        existing = json.loads(_run(["api", "GET", base, "--as", "bot"]))
        count = len(existing.get("data", {}).get("items", []))
        if count:
            _run([
                "api", "DELETE", f"{base}/batch_delete",
                "--as", "bot",
                "--data", json.dumps({"start_index": 0, "end_index": count}),
            ])

        _run([
            "api", "POST", base,
            "--as", "bot",
            "--data", json.dumps({
                "children": [
                    {"block_type": 2, "text": {"elements": [{"text_run": {"content": text}}]}},
                ],
            }, ensure_ascii=False),
        ])


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
