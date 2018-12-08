"""Webhook event handlers."""
import sys

from gidgethub.routing import Router


router = Router()  # pylint: disable=invalid-name


@router.register('ping')
async def on_ping(event):
    """React to ping webhook event."""
    print(f'pinged {event!r}', file=sys.stderr)


@router.register('integration_installation', action='created')
@router.register('installation', action='created')  # deprecated alias
async def on_install(event):
    """React to GitHub App integration installation webhook event."""
    # TODO: store install id and token
    # get_install_token(
    #     app_id=, private_key=,
    #     access_token_url=payload["installation"]["access_tokens_url"],
    # )
    print(f'installed {event!r}', file=sys.stderr)