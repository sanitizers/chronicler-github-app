"""Webhook event handlers."""
from datetime import datetime
from functools import wraps
from io import StringIO
import re
import sys

import attr
from check_in.github_api import DEFAULT_USER_AGENT as CHECK_IN_USER_AGENT
from check_in.github_checks_requests import (
    NewCheckRequest, UpdateCheckRequest,
    to_gh_query,
)
from gidgethub.routing import Router
from unidiff import PatchSet

from .utils import GitHubAPIClient


_NEWS_FRAGMENT_RE = re.compile(
    r'news/[^\./]+\.(removal|feature|bugfix|doc|vendor|trivial)$',
)
"""Regexp for the valid location of news fragments."""


router = Router()  # pylint: disable=invalid-name


def listen_to_event_actions(event_name, actions):
    """Subscribe to multiple events."""
    def decorator(original_function):
        def wrapper(*args, **kwargs):
            return original_function(*args, **kwargs)
        for action in actions:
            wrapper = router.register(event_name, action=action)(wrapper)
        return wraps(original_function)(wrapper)
    return decorator


@router.register('ping')
async def on_ping(event, github_app):
    """React to ping webhook event."""
    print(f'pinged {event!r}', file=sys.stderr)
    print(f'installation={github_app!r}', file=sys.stderr)


@router.register('integration_installation', action='created')
@router.register('installation', action='created')  # deprecated alias
async def on_install(event, app_installation):
    """React to GitHub App integration installation webhook event."""
    print(f'installed {event!r}', file=sys.stderr)
    print(
        f'installed event dat install id {event.data["installation"]["id"]!r}',
        file=sys.stderr,
    )
    print(
        f'installed event delivery_id {event.delivery_id!r}',
        file=sys.stderr,
    )
    print(f'installation={app_installation!r}', file=sys.stderr)


@listen_to_event_actions(
    'pull_request',
    {
        'labeled', 'unlabeled',
        'opened', 'reopened',
        'synchronize',
    },
)
async def on_pr(event, app_installation):
    """React to GitHub App pull request webhook event."""
    diff_url = event.data['pull_request']['diff_url']
    head_branch = event.data['pull_request']['head']['ref']
    head_sha = event.data['pull_request']['head']['sha']
    repo_slug = event.data['repository']['full_name']
    check_runs_base_uri = f'/repos/{repo_slug}/check-runs'
    async with GitHubAPIClient() as gh_api:
        gh_api.requester = (
            f'{gh_api.requester} built with {CHECK_IN_USER_AGENT}'
        )

        resp = await gh_api.post(
            check_runs_base_uri,
            accept='application/vnd.github.antiope-preview+json',
            data=to_gh_query(NewCheckRequest(
                head_branch, head_sha,
                name='Timeline protection',
                started_at=f'{datetime.utcnow().isoformat()}Z',
            )),
            oauth_token=app_installation['access'].token,
        )
        print(
            f'Check suite ID is {resp["check_suite"]["id"]}\n'
            f'Check run ID is {resp["id"]}',
            file=sys.stderr,
        )
        check_runs_updates_uri = f'{check_runs_base_uri}/{resp["id"]:d}'

        diff_text = await gh_api.getitem(
            diff_url,
            oauth_token=app_installation['access'].token,
        )
        diff = PatchSet(StringIO(diff_text))

        update_check_req = UpdateCheckRequest(
            name='Timeline protection',
            status='in_progress',
        )
        resp = await gh_api.patch(
            check_runs_updates_uri,
            accept='application/vnd.github.antiope-preview+json',
            data=to_gh_query(update_check_req),
            oauth_token=app_installation['access'].token,
        )

        news_fragments_added = [
            f for f in diff
            if f.is_added_file and _NEWS_FRAGMENT_RE.search(f.path)
        ]
        print(
            'News fragments are '
            f'{"present" if news_fragments_added else "absent"}',
            file=sys.stderr,
        )

        update_check_req = attr.evolve(
            update_check_req,
            status='completed',
            conclusion=(
                'success' if news_fragments_added
                else 'failure'
            ),
            completed_at=f'{datetime.utcnow().isoformat()}Z',
            output={
                'title': f'{update_check_req.name}: Good to go',
                'text':
                    'The following news fragments found: '
                    f'{news_fragments_added!r}',
                'summary':
                    'Great! This change has been recorded to the chronicles',
            } if news_fragments_added else {
                'title': f'{update_check_req.name}: History fragments missing',
                'text': f'No files matching {_NEWS_FRAGMENT_RE} pattern added',
                'summary':
                    'Oops... This change does not have a record in the '
                    'archives. Just as if it never happened!',
            },
        )
        resp = await gh_api.patch(
            check_runs_updates_uri,
            accept='application/vnd.github.antiope-preview+json',
            data=to_gh_query(update_check_req),
            oauth_token=app_installation['access'].token,
        )

        print(f'got pull_request event', file=sys.stderr)
        print(f'event {event.event!r}', file=sys.stderr)
        print(gh_api)
