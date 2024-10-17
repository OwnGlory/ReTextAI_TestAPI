import asyncio
import logging
import sentry_sdk
from bot import main
from config import bot_env

log = logging.getLogger(__name__)


def configure_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        datefmt='%Y-%m-%d %H:%M:%S',
        format='%(asctime)s - %(module)s - %(lineno)d - %(message)s',
    )

if __name__ == '__main__':
    sentry_sdk.init(bot_env.sentry_dsn)  # Инициализация Sentry
    configure_logging()
    log.info('..... S T A R T .....')
    asyncio.run(main())
