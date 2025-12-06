import sys
from read_config import ConfigLoader
from config.errors import ConfigError, ConfigErrorBundle
from log import info, error


def main():
    loader = ConfigLoader()
    try:
        loader.load_all(collect_errors=True)
        info("配置校验通过")
        sys.exit(0)
    except ConfigErrorBundle as e:
        error(str(e))
        sys.exit(1)
    except ConfigError as e:
        error(str(e))
        sys.exit(1)


if __name__ == '__main__':
    main()

