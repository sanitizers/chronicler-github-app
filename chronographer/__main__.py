"""Cronicler robot runner."""

import asyncio
import logging
import sys

import attr

from octomachinery.app.config import BotAppConfig
from octomachinery.app.runtime.context import RUNTIME_CONTEXT
from octomachinery.app.server.config import WebServerConfig

from . import event_handlers  # noqa: F401; pylint: disable=unused-import
from .server_machinery import run_server_forever


logger = logging.getLogger(__name__)


def run_app():
    """Start up a server using CLI args for host and port."""
    config = BotAppConfig.from_dotenv()
    if len(sys.argv) > 2:
        config = attr.evolve(
            config,
            server=WebServerConfig(*sys.argv[1:3]),
        )
    RUNTIME_CONTEXT.config = config  # pylint: disable=assigning-non-slot
    if config.runtime.debug:  # pylint: disable=no-member
        logging.basicConfig(level=logging.DEBUG)

        from octomachinery.github.config.utils import APP_VERSION
        logger.debug(
            ' App version: %s '.center(50, '='),
            APP_VERSION,
        )
    else:
        logging.basicConfig(level=logging.INFO)

    try:
        asyncio.run(run_server_forever(config))
    except KeyboardInterrupt:
        logger.info(' Exiting the app '.center(50, '='))


__name__ == '__main__' and run_app()  # pylint: disable=expression-not-assigned
