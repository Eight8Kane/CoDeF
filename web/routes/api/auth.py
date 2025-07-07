from fastapi import APIRouter, Depends, Request

from auth.users import get_user_manager, UserManager

auth_page_router = APIRouter()


@auth_page_router.get("/verify/{token}")
async def verify_token(token: str, request: Request, user_manager: UserManager = Depends(get_user_manager)):
    await user_manager.verify(token, request)
