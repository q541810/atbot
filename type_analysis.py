import json
from typing import Tuple, Optional, Any, Dict, List

# 新增：工具函数拆分，降低 parse_msg 的圈复杂度

def _safe_json_load(msg: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(msg)
    except Exception:
        return None


def _is_message_event(event: Dict[str, Any]) -> bool:
    return event.get("post_type") == "message"


def _extract_sender_name(sender: Dict[str, Any]) -> str:
    name = sender.get("card") or sender.get("nickname") or sender.get("user_id") or ""
    return str(name)


def _parse_array_segments(segments: List[Dict[str, Any]]) -> Tuple[str, str]:
    media_types = {
        'image': '图片',
        'record': '语音',
        'voice': '语音',
        'video': '视频',
        'file': '文件'
    }
    text_parts: List[str] = []
    media_url = ''
    for seg in segments:
        t = (seg or {}).get("type")
        data = (seg or {}).get("data", {}) or {}
        if t == "text":
            text_parts.append(str(data.get("text", "")))
        elif t == "at":
            qq = data.get("qq")
            if qq:
                text_parts.append(f"@{qq}")
        elif t == "face":
            pass
        elif t in media_types:
            if t == 'image':
                media_url = data.get('url', '')
            return media_types[t], media_url
    return "文字", "".join(text_parts).strip()


def _parse_raw_message(rm: str) -> Tuple[str, str]:
    media_cq = {
        '[CQ:image': '图片',
        '[CQ:record': '语音',
        '[CQ:voice': '语音',
        '[CQ:video': '视频',
        '[CQ:file': '文件'
    }
    for cq, msg_type in media_cq.items():
        if cq in rm:
            # 提取 url
            url_start = rm.find('url=')
            if url_start != -1:
                url_end = rm.find(']', url_start)
                if url_end != -1:
                    url = rm[url_start + 4:url_end]
                    return msg_type, url
            return msg_type, ''
    return "文字", rm


# 重构后的主函数：仅负责协调、返回结构

def parse_msg(msg: str) -> Optional[Tuple[str, str, int, str]]:
    """
    解析 OneBot/NapCat 的事件消息，提取用于后续逻辑的关键信息。

    返回: (消息类型, 消息内容, 群号, 人名)
    - 消息类型: "文字" | "图片" | "语音" | "视频" | "文件" | "系统"
    - 消息内容: 仅当消息类型为 "文字" 时返回文本内容，其它类型返回空字符串（上层会覆盖为占位符）
    - 群号: 群聊为 group_id，私聊则返回 user_id，用于日志展示
    - 人名: 优先 sender.card，其次 sender.nickname，再次 sender.user_id
    """
    event = _safe_json_load(msg)
    if not event or not _is_message_event(event):
        return None

    message_type = event.get("message_type", "")
    group_id_raw = event.get("group_id") if message_type == "group" else event.get("user_id") or 0
    try:
        group_id = int(group_id_raw)
    except Exception:
        group_id = 0

    sender = event.get("sender", {}) or {}
    name = _extract_sender_name(sender)

    segments = event.get("message")
    message_format = event.get("message_format")
    raw_message = event.get("raw_message", "") or ""

    if isinstance(segments, list) and message_format == "array":
        msg_type, content = _parse_array_segments(segments)
    else:
        msg_type, content = _parse_raw_message(raw_message)

    return msg_type, content, group_id, name