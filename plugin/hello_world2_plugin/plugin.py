import websocket
import json
from demo import 发
def 发消息(target_group_id, current_group_id, message):
    """
    发送消息到指定的群聊
    :param target_group_id: 目标群聊ID
    :param current_group_id: 当前群聊ID
    :param message: 要发送的消息
    :return: None
    """
    发(message, int(target_group_id))
