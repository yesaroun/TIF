import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # SQLite 스레드와 여러 서버 스레드가 연결되도록
        "timeout": 30.0,
        "isolation_level": "IMMEDIATE",  # 트랜젝션 격리 수준
        "detect_types": sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        # 데이터 타입 자동 변환
        # PARSE_DECLTYPES: 선언된 타입 기반 파싱
        # PARSE_COLNAMES: 컬럼명 기반 파싱
        "cached_statements": 256,  # 캐시할 명령 수
        "uri": True,  # URI 형식 데이터베이스 경로 사용
        # "autocommit": False,  # db 엔진 수준 커밋 설정
    },
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,  # Session 객체가 언제 자동으로 SQL 명령어를 데이터베이스에 전송할지 제어한느 설정
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
