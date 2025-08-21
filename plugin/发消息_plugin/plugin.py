def 发消息(target_group_id, current_group_id, message, send=None):
    """
    发送消息到指定的群聊
    :param target_group_id: 目标群聊ID（字符串或数字）
    :param current_group_id: 当前群聊ID（来自上下文插入）
    :param message: 要发送的消息
    :param send: 由消息处理器注入的发送回调，签名为 send(text: str, group_id: int)
    :return: None
    """
    if send is None:
        print("错误：发消息插件未获得 send 回调，无法发送")
        return
    try:
        gid = int(target_group_id)
    except Exception:
        print(f"错误：目标群ID无效: {target_group_id}")
        return
    send(str(message), gid)
