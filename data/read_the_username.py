import os
import re
from typing import Dict, Optional, Union

import json
import websockets

from log import info, warning

# 存储映射的文件名（和本文件在同一目录）
MAPPING_FILENAME = "Group_members_name.txt"


def _mapping_path() -> str:
    return os.path.join(os.path.dirname(__file__), MAPPING_FILENAME)


def _load_mapping(file_path: Optional[str] = None) -> Dict[str, str]:
    """
    读取 QQ 号到用户名的映射表。
    支持形如 "1234567890 : Nick" 或 "1234567890:Nick" 的格式，忽略空行与注释行。
    注意：如果某行格式不符合预期，将被跳过，以避免影响程序运行。
    """
    path = file_path or _mapping_path()
    mapping: Dict[str, str] = {}
    if not os.path.exists(path):
        return mapping
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                # 兼容半角/全角冒号，并容忍多余空格
                sep_index = line.find(":")
                if sep_index == -1:
                    # 尝试全角冒号
                    sep_index = line.find("：")
                    if sep_index == -1:
                        continue
                left = line[:sep_index].strip()
                right = line[sep_index + 1 :].strip()
                # 从左侧提取纯数字 QQ 号
                m = re.search(r"\d+", left)
                if not m:
                    continue
                qq = m.group(0)
                if qq and right:
                    mapping[qq] = right
    except Exception as e:
        warning(f"读取 {path} 失败: {e}")
    return mapping


def _append_mapping(qq号: str, 昵称: str, file_path: Optional[str] = None) -> None:
    path = file_path or _mapping_path()
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{qq号} : {昵称}\n")
        info(f"已记录用户 {qq号} -> {昵称}")
    except Exception as e:
        warning(f"写入 {path} 失败: {e}")


async def 获取或新增用户名(qq号: Union[int, str], napcat_host: str, napcat_port: int, 群号: Optional[int] = None) -> str:
    """
    根据 QQ 号获取用户名：
    - 若在 Group_members_name.txt 中已存在，则直接返回
    - 若不存在，则通过 OneBot WebSocket Action 查询（优先群名片，回退陌生人昵称），成功后写入文件并返回
    - 查询失败则回退为原 QQ 号字符串
    """
    qq_str = str(qq号)
    映射 = _load_mapping()
    if qq_str in 映射:
        return 映射[qq_str]

    try:
        昵称 = await 查询用户名_ws(int(qq_str), napcat_host, napcat_port, group_id=群号)
    except Exception as e:
        warning(f"通过 WS 查询昵称失败[{qq_str}]: {e}")
        昵称 = None

    if 昵称:
        _append_mapping(qq_str, 昵称)
        return 昵称
    # 查询失败时回退为原 QQ 号字符串
    return qq_str


async def 替换消息中的at(消息内容: str, napcat_host: str, napcat_port: int, *, bot_qq: Optional[int] = None, bot_name: Optional[str] = None, 群号: Optional[int] = None) -> str:
    """
    将消息中形如 @1234567890 的片段替换为 @昵称。
    - 必须保留 @ 符号，只替换数字为昵称
    - 对机器人本体（bot_qq）替换为 @bot_name
    - 出错时保持原样，绝不抛异常
    - 支持在群环境下优先取群名片
    - 支持 QQ 号长度 5~12 位（常见范围）
    """
    pattern = re.compile(r"@(\d{5,12})")
    result_parts = []
    last_idx = 0

    for m in pattern.finditer(消息内容):
        result_parts.append(消息内容[last_idx:m.start()])
        qq = m.group(1)
        rep = m.group(0)  # 默认保持原样
        try:
            if bot_qq is not None and bot_name and int(qq) == int(bot_qq):
                rep = f"@{bot_name}"
            else:
                昵称 = await 获取或新增用户名(qq, napcat_host, napcat_port, 群号=群号)
                # 查询失败时 获取或新增用户名 会返回 qq 本身，这时保持原样不替换
                if 昵称 and str(昵称) != str(qq):
                    rep = f"@{昵称}"
        except Exception as e:
            warning(f"替换 @ 用户名失败[{qq}]: {e}")
        result_parts.append(rep)
        last_idx = m.end()

    result_parts.append(消息内容[last_idx:])
    return "".join(result_parts)


__all__ = [
    "获取或新增用户名",
    "替换消息中的at",
]


def 查询用户名(qq号,napcat_host,napcat_port):
    base = f"http://{napcat_host}:{napcat_port}"
    try:
        # 尝试 OneBot/Napcat HTTP API: GET /get_stranger_info?user_id=xxx
        url = f"{base}/get_stranger_info"
        resp = requests.get(url, params={"user_id": qq号}, timeout=5)
        # 优先尝试解析 JSON
        try:
            data = resp.json()
        except Exception:
            # 非 JSON 响应（例如 404/HTML），打印部分文本用于诊断并返回 None
            text = resp.text[:120]
            info(f"查询用户名返回非JSON，status={resp.status_code}，片段: {text}")
            return None
        # 兼容不同封装：有的直接返回 data，有的嵌套在 data 字段
        payload = data.get("data", data)
        nick = payload.get("nickname") or payload.get("nick") or payload.get("name")
        if nick:
            info("记录了用户qq号为{}的用户名{}".format(qq号, nick))
            return nick
        return None
    except Exception as e:
        info(f"查询用户名失败: {e}")
        return None

async def _onebot_ws_action(action: str, params: dict, napcat_host: str, napcat_port: int, echo: str) -> Optional[dict]:
    uri = (f"ws://{napcat_host}:{napcat_port}/")
    try:
        async with websockets.connect(uri) as ws:
            req = {
                "action": action,
                "params": params,
                "echo": echo,
            }
            await ws.send(json.dumps(req))
            while True:
                resp_text = await ws.recv()
                try:
                    data = json.loads(resp_text)
                except Exception:
                    continue
                if isinstance(data, dict) and data.get("echo") == echo:
                    return data
    except Exception as e:
        from log import warning
        warning(f"WS action {action} 失败: {e}")
    return None

async def 查询用户名_ws(qq号: int, napcat_host: str, napcat_port: int, group_id: Optional[int] = None) -> Optional[str]:
    from log import info, warning
    # 优先查询群名片
    if group_id is not None:
        echo = f"get_group_member_info_{group_id}_{qq号}"
        resp = await _onebot_ws_action(
            "get_group_member_info",
            {"group_id": int(group_id), "user_id": int(qq号)},
            napcat_host,
            napcat_port,
            echo,
        )
        if resp and isinstance(resp, dict):
            payload = resp.get("data", resp)
            # OneBot有时有 status/retcode 包装
            if isinstance(payload, dict) and (payload.get("card") or payload.get("nickname")):
                nick = payload.get("card") or payload.get("nickname")
                if nick:
                    info(f"通过群({group_id})查询到 {qq号} 的昵称: {nick}")
                    return nick
            # 兼容 status/data 结构
            if resp.get("status") == "ok" and isinstance(resp.get("data"), dict):
                data = resp["data"]
                nick = data.get("card") or data.get("nickname")
                if nick:
                    info(f"通过群({group_id})查询到 {qq号} 的昵称: {nick}")
                    return nick
            # 若群查询失败则回退
    # 回退陌生人信息
    echo = f"get_stranger_info_{qq号}"
    resp = await _onebot_ws_action(
        "get_stranger_info",
        {"user_id": int(qq号)},
        napcat_host,
        napcat_port,
        echo,
    )
    if resp and isinstance(resp, dict):
        # 既可能 data 在顶层，也可能在 data 字段
        payload = resp.get("data", resp)
        if isinstance(payload, dict) and (payload.get("nickname") or payload.get("name") or payload.get("user_displayname")):
            nick = payload.get("nickname") or payload.get("name") or payload.get("user_displayname")
            return nick
        if resp.get("status") == "ok" and isinstance(resp.get("data"), dict):
            data = resp["data"]
            nick = data.get("nickname") or data.get("name") or data.get("user_displayname")
            return nick
    warning(f"WS 查询 {qq号} 昵称失败，返回: {json.dumps(resp) if resp else 'None'}")
    return None