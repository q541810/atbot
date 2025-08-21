import time
import random

# 直接导入主程序中的发函数和撤回函数
from demo import 发, 撤回

def get_current_time(group_id):
    发(str(time.time()), group_id)

def hello(text, group_id):
    发("你好"+text+"，当前时间为："+str(time.time()), group_id)

def 撤回_plugin(message_id, group_id):
    """撤回指定消息
    Args:
        message_id: 要撤回的消息ID
        group_id: 群组ID
    """
    try:
        撤回(group_id, message_id)
        撤回成功发言=["撤回成功啦~","完成了喵！","撤回完成了喵！"]
        发(random.choice(撤回成功发言), group_id)

    except Exception as e:
        发(f"撤回失败: {str(e)}", group_id)
def 请安(name,group_id):
    发(f"麦麦给{name}请安咯~~~")
