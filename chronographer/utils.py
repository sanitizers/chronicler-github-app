"""Helper utils."""
import sys
import time

import aiohttp
import gidgethub.aiohttp
import jwt


APP_VERSION = 'unknown'  # TODO: add "/1.0" as in version
USER_AGENT = (
    f'Chronographer-Bot/{APP_VERSION}'
    ' (+https://github.com/sanitizers/chronographer-github-app)'
)


class SecretStr(str):
    """String that censors its __repr__ if called from another repr."""

    def __repr__(self):
        """Produce a string representation."""
        frame_depth = 1

        try:
            while True:
                f = sys._getframe(frame_depth)
                frame_depth += 1

                if f.f_code.co_name == "__repr__":
                    return "<SECRET>"
        except ValueError:
            pass

        return super().__repr__()


def get_gh_jwt(app_id, private_key):
    """Create a signed JWT, valid for 60 seconds."""
    now = int(time.time())
    payload = {
        'iat': now,
        'exp': now + 60,
        'iss': app_id,
    }
    return jwt.encode(
        payload,
        key=private_key,
        algorithm='RS256',
    ).decode('utf-8')


async def get_install_token(*, app_id, private_key, access_token_url):
    """Retrieve installation access token from GitHub API."""
    gh_jwt = get_gh_jwt(app_id, private_key)
    async with aiohttp.ClientSession() as session:
        gh_api = gidgethub.aiohttp.GitHubAPI(
            session,
            USER_AGENT,
            jwt=gh_jwt,
        )
        return await gh_api.getitem(access_token_url)['token']
