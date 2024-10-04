from fastapi import FastAPI, Form
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from .config import CLIENT_ID, CLIENT_SECRET

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="sso-auth")

oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    client_kwargs={
        'scope': 'email openid profile',
        'redirect_url': 'http://localhost:8000/auth'
    }
)

templates = Jinja2Templates(directory="templates")

@app.get("/")
def index(request: Request):
    user = request.session.get('user')
    if user:
        return RedirectResponse('welcome')

    return templates.TemplateResponse(
        name="index.html",
        context={"request": request}
    )

@app.get('/welcome')
def welcome(request: Request):
    user = request.session.get('user')
    additional_data = request.session.get('additional_data')
    if not user:
        return RedirectResponse('/')
    return templates.TemplateResponse(
        name='welcome.html',
        context={'request': request, 'user': user, 'additional_data': additional_data}
    )

@app.post("/sign_in_with_google")
async def signin(request: Request):
    form_data = await request.form(     )
    additional_data = {"sport": form_data.get('sport'), "location": form_data.get('location')}
    request.session['additional_data'] = additional_data

    url = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, url)

@app.get('/auth')
async def auth(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as e:
        return templates.TemplateResponse(
            name='error.html',
            context={'request': request, 'error': e.error}
        )
    user = token.get('userinfo')
    if user:
        request.session['user'] = dict(user)

    return RedirectResponse('welcome')

@app.get('/logout')
def logout(request: Request):
    request.session.pop('user')
    request.session.pop('additional_data')
    request.session.clear()
    return RedirectResponse('/')