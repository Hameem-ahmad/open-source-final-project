from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import load_settings
from app.database import get_db
from app.models import User


auth_header = HTTPBearer(auto_error=False)
app_settings = load_settings()


def check_password(typed_password: str, saved_password: str) -> bool:
    return typed_password == saved_password


def make_login_token(user_id: int, user_role: str) -> str:
    token_data = {
        "sub": str(user_id),
        "role": user_role,
    }
    expire_time = datetime.utcnow() + timedelta(
        minutes=app_settings.access_token_expire_minutes
    )
    token_data["exp"] = expire_time
    return jwt.encode(
        token_data,
        app_settings.secret_key,
        algorithm=app_settings.algorithm,
    )


def get_logged_in_user(
    auth_info: HTTPAuthorizationCredentials = Depends(auth_header),
    db: Session = Depends(get_db),
) -> User:
    if auth_info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = auth_info.credentials

    try:
        decoded = jwt.decode(
            token,
            app_settings.secret_key,
            algorithms=[app_settings.algorithm],
        )
        user_id = decoded.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def must_be_role(*allowed_roles: str):
    def check_role(logged_in_user: User = Depends(get_logged_in_user)) -> User:
        if logged_in_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return logged_in_user

    return check_role
