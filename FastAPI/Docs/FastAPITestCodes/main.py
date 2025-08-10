from typing import Dict, Any

from fastapi import FastAPI

app = FastAPI(
    title="FastAPI 테스트 애플리케이션",
    description="FastAPI 학습 및 테스트를 위한 기본 애플리케이션",
    version="1.0.0",
)


@app.get("/")
async def read_root() -> Dict[str, str]:
    """루트 엔드포인트"""
    return {
        "message": "안녕하세요! FastAPI 테스트 애플리케이션에 오신 것을 환영합니다!"
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """헬스체크 엔드포인트"""
    return {"status": "healthy", "message": "서버가 정상적으로 작동 중입니다"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None) -> Dict[str, Any]:
    """아이템 조회 엔드포인트"""
    result = {"item_id": item_id}
    if q:
        result.update({"q": q})
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
