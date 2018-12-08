"""GitHub App/bot configuration."""

import attr
import environ
import envparse

envparse.Env.read_envfile()


def get_config():
    return environ.to_config(BotAppConfig)


@environ.config
class BotAppConfig:

    @environ.config
    class GitHubAppIntegrationConfig:
        app_id = environ.var(name='GITHUB_APP_IDENTIFIER')
        private_key = environ.var(name='GITHUB_PRIVATE_KEY')
        webhook_secret = environ.var(None, name='GITHUB_WEBHOOK_SECRET')

    @environ.config
    class WebServerConfig:
        host = environ.var('0.0.0.0', name='HOST')
        port = environ.var(8080, name='PORT', converter=int)

    __version__ = 0, 0, 1
    debug = environ.bool_var(False, name='DEBUG')
    env = environ.var(
        'prod', name='ENV',
        validator=attr.validators.in_(('dev', 'prod')),
    )
    github_app = environ.group(GitHubAppIntegrationConfig)
    github_app_url = 'https://github.com/apps/chronographer'
    name = 'Chronographer'
    server = environ.group(WebServerConfig)
    user_agent = (
        f'{name}-Bot/{".".join(map(str, __version__))}'
        f' (+{github_app_url})'
    )