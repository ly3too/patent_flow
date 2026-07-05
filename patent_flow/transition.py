"""Atomic state transition — the only path for any state write."""
import os
import subprocess
from .state_machine import validate_transition
from .store import BitableStore, LarkIM, LarkDoc


def transition(
    case_no: str,
    from_node: str,
    to_node: str,
    evidence: str,
    record_id: str,
    chat_id: str,
    doc_token: str,
    state_block_id: str,
    case_title: str,
) -> None:
    validate_transition(from_node, to_node)

    app_token = os.environ["LEDGER_APP_TOKEN"]
    bitable = BitableStore(
        app_token=app_token,
        main_table_id=os.environ["LEDGER_MAIN_TABLE"],
        events_table_id=os.environ["LEDGER_EVENTS_TABLE"],
    )
    im = LarkIM()
    doc = LarkDoc()

    # 1. append-only event log (write first — never lose audit trail)
    bitable.append_event(
        case_no=case_no,
        source="agent",
        event_type="节点跳转",
        summary=f"{from_node} → {to_node}: {evidence}",
    )

    # 2. update master document agent:state block
    new_state_xml = _render_state_xml(case_no, to_node)
    doc.update_block(doc_token, state_block_id, new_state_xml)

    # 3. update bitable master table
    bitable.update_case(record_id, {"当前节点": to_node})

    # 4. sync group chat name + announcement + broadcast
    new_name = f"[{case_no}] {case_title} - {to_node}"
    announcement = _render_announcement(case_no, to_node)
    im.update_chat(chat_id, name=new_name)
    _set_announcement_with_fallback(im, chat_id, announcement)
    im.send(chat_id, f"🔄 节点跳转 {from_node} → {to_node}\n依据：{evidence}")


def _set_announcement_with_fallback(im: LarkIM, chat_id: str, announcement: str) -> None:
    """群公告 needs `im:chat.announcement:read`/`write_only` enabled for the
    app in the Feishu console (not something `auth login` alone can grant —
    see store.py's `LarkIM.set_announcement` docstring). If that's missing,
    degrade to a pinned status message instead of failing the whole
    transition."""
    try:
        im.set_announcement(chat_id, announcement)
    except subprocess.CalledProcessError:
        message_id = im.send(chat_id, announcement)
        im.pin(chat_id, message_id)


def _render_state_xml(case_no: str, node: str) -> str:
    return f"<p>节点：{node}</p>"


def _render_announcement(case_no: str, node: str) -> str:
    return f"📌 [{case_no}] 当前节点：{node}"
