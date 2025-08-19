from typing import Annotated
from fastapi import FastAPI, Depends, Header, HTTPException, status

app = FastAPI()


def auth_token(x_token: Annotated[str | None, Header()] = None):
    if x_token != "super-secret":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    return {"scopes": ["read", "write"]}


Auth = Annotated[dict, Depends(auth_token)]


@app.get("/secure")
def secure_area(auth: Auth):
    return {"ok": True, "auth": auth}
