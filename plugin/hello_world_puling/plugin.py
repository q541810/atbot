import time
import random

# 取消对主程序中发/撤回的直接依赖，改为使用注入的回调

def get_current_time(group_id=None, send=None):
    if send and group_id is not None:
        send(str(time.time()), group_id)

def hello(text, group_id=None, send=None):
    if send and group_id is not None:
        send("你好" + text + "，当前时间为：" + str(time.time()), group_id)

def 撤回_plugin(message_id, group_id=None, revoke=None, send=None):
    """撤回指定消息
    Args:
        message_id: 要撤回的消息ID
        group_id: 群组ID
    """
    try:
        if revoke and group_id is not None:
            revoke(group_id, message_id)
        撤回成功发言 = ["撤回成功啦~", "完成了喵！", "撤回完成了喵！"]
        if send and group_id is not None:
            send(random.choice(撤回成功发言), group_id)
    except Exception as e:
        if send and group_id is not None:
            send(f"撤回失败: {str(e)}", group_id)

def 请安(name, group_id=None, send=None):
    if send and group_id is not None:
        send(f"麦麦给{name}请安咯~~~", group_id)
