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
        out = _run([
            "base", "+query",
            "--app-token", self.app_token,
            "--table-id", self.main_table_id,
            "--filter", f'CurrentValue.[案号] = "{case_no}"',
        ])
        rows = json.loads(out)
        if not rows:
            raise KeyError(f"Case not found: {case_no}")
        return rows[0]["fields"]

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
