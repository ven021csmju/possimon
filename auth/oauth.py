from authlib.integrations.starlette_client import OAuth
from core.config import settings

oauth = OAuth()

oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

oauth.register(
    name='line',
    client_id=settings.LINE_CHANNEL_ID,
    client_secret=settings.LINE_CHANNEL_SECRET,
    access_token_url='https://api.line.me/oauth2/v2.1/token',
    authorize_url='https://access.line.me/oauth2/v2.1/authorize',
    api_base_url='https://api.line.me/',
    client_kwargs={
        'scope': 'profile',
        'token_endpoint_auth_method': 'client_secret_post',
    }
)

oauth.register(
    name='facebook',
    client_id=settings.FACEBOOK_APP_ID,
    client_secret=settings.FACEBOOK_APP_SECRET,
    access_token_url='https://graph.facebook.com/v19.0/oauth/access_token',
    authorize_url='https://www.facebook.com/v19.0/dialog/oauth',
    api_base_url='https://graph.facebook.com/v19.0/',
    client_kwargs={
        "scope": "email public_profile"
    }
)
