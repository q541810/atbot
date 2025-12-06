import os
import re
import asyncio
from typing import Dict, Optional, Union, Any

import json
import websockets

from log import info, warning

# 存储映射的文件名（和本文件在同一目录）
MAPPING_FILENAME = "Group_members_name.txt"
_LOCK = asyncio.Lock()


def _mapping_path() -> str:
    return os.path.join(os.path.dirname(__file__), MAPPING_FILENAME)


def _load_mapping(file_path: Optional[str] = None) -> Dict[str, str]:
    """读取 QQ 号到用户名的映射表，支持冒号格式，忽略无效行。"""
    path = file_path or _mapping_path()
    mapping: Dict[str, str] = {}
    if not os.path.exists(path):
        return mapping
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                sep = ":" if ":" in line else "："
                if sep not in line:
                    continue
                left, right = [part.strip() for part in line.split(sep, 1)]
                m = re.search(r"\d+", left)
                if m and right:
                    mapping[m.group(0)] = right
    except Exception as e:
        warning(f"读取 {path} 失败: {e}")
    return mapping


async def _append_mapping(qq号: str, 昵称: str, file_path: Optional[str] = None) -> None:
    """追加映射，若超过100条，删除最旧条目。"""
    async with _LOCK:
        path = file_path or _mapping_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            mapping = _load_mapping(path)
            if len(mapping) >= 100:
                oldest_qq = next(iter(mapping))
                with open(path, "r", encoding="utf-8") as f:
                    lines = [line for line in f if not (line.strip().startswith(str(oldest_qq)) and (":" in line or "：" in line)) or line.strip().startswith("#")]
                with open(path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"{qq号} : {昵称}\n")
            info(f"已记录用户 {qq号} -> {昵称}")
        except Exception as e:
            warning(f"写入 {path} 失败: {e}")


async def 获取或新增用户名(qq号: Union[int, str], napcat_host: str, napcat_port: int, 群号: Optional[int] = None, websocket=None) -> str:
    """获取或查询并新增用户名，失败返回QQ号字符串。"""
    qq_str = str(qq号)
    映射 = _load_mapping()
    if qq_str in 映射:
        return 映射[qq_str]
    try:
        昵称 = await 查询用户名_ws(int(qq_str), napcat_host, napcat_port, group_id=群号, websocket=websocket)
        if 昵称:
            await _append_mapping(qq_str, 昵称)
            return 昵称
    except Exception as e:
        warning(f"通过 WS 查询昵称失败[{qq_str}]: {e}")
    return qq_str


async def 替换消息中的at(消息内容: str, napcat_host: str, napcat_port: int, *, bot_qq: Optional[int] = None, bot_name: Optional[str] = None, 群号: Optional[int] = None, websocket=None) -> str:
    """替换消息中的@QQ为@昵称，支持机器人自身替换。"""
    pattern = re.compile(r"@(\d{5,12})")
    result_parts = []
    last_idx = 0
    for m in pattern.finditer(消息内容):
        result_parts.append(消息内容[last_idx:m.start()])
        qq = m.group(1)
        rep = m.group(0)
        try:
            if bot_qq and bot_name and int(qq) == bot_qq:
                rep = f"@{bot_name}"
            else:
                昵称 = await 获取或新增用户名(qq, napcat_host, napcat_port, 群号=群号, websocket=websocket)
                if 昵称 != qq:
                    rep = f"@{昵称}"
        except Exception as e:
            warning(f"替换 @ 用户名失败[{qq}]: {e}")
        result_parts.append(rep)
        last_idx = m.end()
    result_parts.append(消息内容[last_idx:])
    return "".join(result_parts)


__all__ = ["获取或新增用户名", "替换消息中的at"]


async def _onebot_ws_action(action: str, params: dict, napcat_host: str, napcat_port: int, echo: str, websocket=None) -> Optional[dict]:
    """执行OneBot WS动作并等待响应。"""
    # 目前查询类操作依然新建连接，避免与主循环竞争读取
    uri = f"ws://{napcat_host}:{napcat_port}/"
    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({"action": action, "params": params, "echo": echo}))
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(msg)
                    if isinstance(data, dict) and data.get("echo") == echo:
                        return data
                except asyncio.TimeoutError:
                    break
    except Exception as e:
        warning(f"WS action {action} 失败: {e}")
    return None


async def 查询用户名_ws(qq号: int, napcat_host: str, napcat_port: int, group_id: Optional[int] = None, websocket=None) -> Optional[str]:
    """优先查询群名片，否则回退陌生人信息。"""
    from log import info, warning
    if group_id:
        resp = await _onebot_ws_action("get_group_member_info", {"group_id": group_id, "user_id": qq号}, napcat_host, napcat_port, f"get_group_member_info_{group_id}_{qq号}", websocket=websocket)
        if resp and resp.get("status") == "ok":
            data = resp["data"]
            nick = data.get("card") or data.get("nickname")
            if nick:
                info(f"通过群({group_id})查询到 {qq号} 的昵称: {nick}")
                return nick
    resp = await _onebot_ws_action("get_stranger_info", {"user_id": qq号}, napcat_host, napcat_port, f"get_stranger_info_{qq号}", websocket=websocket)
    if resp and resp.get("status") == "ok":
        data = resp["data"]
        nick = data.get("nickname") or data.get("name") or data.get("user_displayname")
        if nick:
            return nick
    warning(f"WS 查询 {qq号} 昵称失败")
    return None
