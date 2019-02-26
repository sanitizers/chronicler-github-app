"""Interaction with GitHub API."""

from collections import defaultdict
from contextlib import AbstractAsyncContextManager
import logging
import types
import typing

from aiohttp.client_exceptions import ClientConnectorError
import attr
from gidgethub.sansio import Event

from octomachinery.github.api.client import GitHubAPIClient
from octomachinery.github.config.app import GitHubAppIntegrationConfig
from octomachinery.github.models import (
    GitHubAppInstallation, GitHubInstallationAccessToken,
)
from octomachinery.utils.asynctools import (
    amap, dict_to_kwargs_cb,
)

from .utils import (
    get_gh_jwt,
)


logger = logging.getLogger(__name__)


GH_INSTALL_EVENTS = {'integration_installation', 'installation'}


@attr.dataclass
class GitHubApp(AbstractAsyncContextManager):
    """GitHub API wrapper."""

    _config: GitHubAppIntegrationConfig

    def __attrs_post_init__(self):
        """Initialize installations store."""
        # pylint: disable=attribute-defined-outside-init
        self._installations = defaultdict(dict)

    async def event_from_request(self, request):
        """Get an event object out of HTTP request."""
        event = Event.from_http(
            request.headers,
            await request.read(),
            secret=self._config.webhook_secret,
        )
        await self.pre_process_webhook_event(event)
        return event

    async def pre_process_webhook_event(self, event):
        """Get an event object out of HTTP request."""
        action = event.data.get('action')
        if event.event in GH_INSTALL_EVENTS and action == 'created':
            await self.add_installation(event)

    async def __aenter__(self) -> 'GitHubApp':
        """Store all installations data before starting."""
        # pylint: disable=attribute-defined-outside-init
        try:
            self._installations = await self.get_installations()
        except ClientConnectorError as client_error:
            logger.info('It looks like the GitHub API is offline...')
            logger.error(
                'The following error has happened while trying to grab '
                'installations list: %s',
                client_error,
            )
            self._installations = defaultdict(dict)
        return self

    async def __aexit__(
            self,
            exc_type: typing.Optional[typing.Type[BaseException]],
            exc_val: typing.Optional[BaseException],
            exc_tb: typing.Optional[types.TracebackType],
    ) -> typing.Optional[bool]:
        """Wipe out the installation store."""
        # pylint: disable=attribute-defined-outside-init
        self._installations = defaultdict(dict)

    @property
    def gh_jwt(self):
        """Generate app's JSON Web Token."""
        return get_gh_jwt(self._config.app_id, self._config.private_key)

    async def get_install_token(self, *, access_token_url):
        """Retrieve installation access token from GitHub API."""
        gh_jwt = get_gh_jwt(self._config.app_id, self._config.private_key)
        async with GitHubAPIClient() as gh_api:
            return GitHubInstallationAccessToken(**(await gh_api.post(
                access_token_url,
                data=b'',
                jwt=gh_jwt,
                accept='application/vnd.github.machine-man-preview+json',
            )))

    async def add_installation(self, event):
        """Retrieve an installation creds from store."""
        install = event.data['installation']
        install_id = install['id']
        self._installations[install_id] = {
            'data': GitHubAppInstallation(install),
            'access': await self.get_install_token(
                access_token_url=install['access_tokens_url'],
            ),
        }
        return self._installations[install_id]

    async def get_installation(self, event):
        """Retrieve an installation creds from store."""
        if event.event == 'ping':
            return None

        install_id = event.data['installation']['id']
        return self._installations.get(install_id)

    async def get_installations(self):
        """Retrieve all installations with access tokens via API."""
        installations = defaultdict(dict)
        async with GitHubAPIClient() as gh_api:
            async for install in amap(
                    dict_to_kwargs_cb(GitHubAppInstallation),
                    gh_api.getiter(
                        '/app/installations',
                        jwt=self.gh_jwt,
                        accept=''
                        'application/vnd.github.machine-man-preview+json',
                    ),
            ):
                installations[install.id] = {
                    'data': install,
                    'access': await self.get_install_token(
                        access_token_url=install.access_tokens_url,
                    ),
                }
        return installations
