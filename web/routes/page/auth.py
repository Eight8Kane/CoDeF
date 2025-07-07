from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from app.templates import templates
from auth.users import UserManager, get_user_manager


auth_router = APIRouter(tags=["auth"])


@auth_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    context = {
        'request': request
    }

    return templates.TemplateResponse('auth/login.html', context)


@auth_router.get("/sign_up", response_class=HTMLResponse)
async def sign_up_page(request: Request):
    context = {
        'request': request
    }

    return templates.TemplateResponse('auth/sign_up.html', context)


@auth_router.get("/signed_up", response_class=HTMLResponse)
async def inform_page(request: Request):
    context = {
        'request': request,
        'message': 'An email has been sent to the registered email address. '
                   'Please check your email and verify your email address.'
    }

    return templates.TemplateResponse('auth/inform.html', context)


@auth_router.get("/verify/{token}")
async def verify_token(token: str, request: Request, user_manager: UserManager = Depends(get_user_manager)):
    try:
        await user_manager.verify(token, request)

        context = {
            'request': request,
            'message': 'Your email address has been verified. You can now sign in to CoDeF.'
        }
    except:
        context = {
            'request': request,
            'status': 'error',
            'message': 'Email address verification failed. '
                       'The authentication token is invalid or the email has already been verified.'
        }

    return templates.TemplateResponse('auth/inform.html', context)
