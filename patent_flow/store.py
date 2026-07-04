"""Thin wrapper around lark-cli for all Feishu read/write operations."""
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


class BitableStore:
    def __init__(self, app_token: str, main_table_id: str, events_table_id: str):
        self.app_token = app_token
        self.main_table_id = main_table_id
        self.events_table_id = events_table_id

    def get_case(self, case_no: str) -> dict:
        """Returns the record's fields plus its bitable `_record_id`, needed
        by anything that will later call `update_case()`/`transition()`."""
        out = _run([
            "base", "+query",
            "--app-token", self.app_token,
            "--table-id", self.main_table_id,
            "--filter", f'CurrentValue.[案号] = "{case_no}"',
        ])
        rows = json.loads(out)
        if not rows:
            raise KeyError(f"Case not found: {case_no}")
        row = rows[0]
        return {**row["fields"], "_record_id": row["record_id"]}

    def get_case_by_chat_id(self, chat_id: str) -> dict:
        """一案一群：群 ID 反查案件（design.md §6.1）。"""
        out = _run([
            "base", "+query",
            "--app-token", self.app_token,
            "--table-id", self.main_table_id,
            "--filter", f'CurrentValue.[群ID] = "{chat_id}"',
        ])
        rows = json.loads(out)
        if not rows:
            raise KeyError(f"No case found for chat_id: {chat_id}")
        return rows[0]["fields"]

    def list_cases_by_node(self, node: str) -> list[dict]:
        """Used by cron scans (S6/S8) to find every case currently sitting
        on a given state-machine node."""
        out = _run([
            "base", "+query",
            "--app-token", self.app_token,
            "--table-id", self.main_table_id,
            "--filter", f'CurrentValue.[当前节点] = "{node}"',
        ])
        rows = json.loads(out)
        return [row["fields"] for row in rows]

    def update_case(self, record_id: str, fields: dict) -> None:
        _run([
            "base", "+record-update",
            "--app-token", self.app_token,
            "--table-id", self.main_table_id,
            "--record-id", record_id,
            "--fields", json.dumps(fields),
        ])

    def append_event(self, case_no: str, source: str, event_type: str,
                     summary: str, detail_url: str = "") -> None:
        _run([
            "base", "+record-create",
            "--app-token", self.app_token,
            "--table-id", self.events_table_id,
            "--fields", json.dumps({
                "案号": case_no,
                "来源": source,
                "事件类型": event_type,
                "摘要": summary,
                "详情链接": detail_url,
            }),
        ])


class LarkIM:
    def send(self, chat_id: str, text: str) -> None:
        _run([
            "im", "+send",
            "--receive-id", chat_id,
            "--msg-type", "text",
            "--content", json.dumps({"text": text}),
        ])

    def update_chat(self, chat_id: str, name: str | None = None,
                    announcement: str | None = None) -> None:
        args = ["im", "+chat-update", "--chat-id", chat_id]
        if name:
            args += ["--name", name]
        if announcement:
            args += ["--announcement", announcement]
        _run(args)


class LarkDoc:
    def update_block(self, doc_token: str, block_id: str, content: str) -> None:
        _run([
            "docs", "+update",
            "--doc", doc_token,
            "--command", "block_replace",
            "--block-id", block_id,
            "--content", content,
        ])
