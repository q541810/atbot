from read_config import ConfigLoader
from log import info


def mask(v):
    if not isinstance(v, str):
        return v
    if len(v) <= 8:
        return '***'
    return '***' + v[-4:]


def main():
    loader = ConfigLoader()
    data = loader.load_all(collect_errors=True)
    adapter = data['adapter']
    bot = data['bot']
    adaptive = data['adaptive']
    info(f"napcat {adapter['napcat_server']['host']}:{adapter['napcat_server']['port']}")
    info(f"bot {bot['bot']['bot的名字']} qq={bot['bot']['bot的qq号']}")
    info(f"replyer url={adaptive['回复模型_url']} key={mask(adaptive['回复模型_key'])} model={adaptive['回复模型_model']}")
    info(f"judge url={adaptive['判断模型_url']} key={mask(adaptive['判断模型_key'])} model={adaptive['判断模型_model']}")
    info(f"picture switch={adaptive['图片模型_switch']} url={adaptive['图片模型_url']} key={mask(adaptive['图片模型_key'])} model={adaptive['图片模型_model']}")


if __name__ == '__main__':
    main()

