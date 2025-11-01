import redis
import uuid
import time


class SimpleLock:
    def __init__(self, redis_client, resource_name, ttl=10000):
        """
        Args:
            redis_client: Redis client
            resource_name: 락을 걸 리소스 이름
            ttl: Time To Live (밀리초)
        """
        self.redis_client = redis_client
        self.resource_name = resource_name
        self.ttl = ttl
        self.lock_value = str(uuid.uuid4())  # 고유 식별자

    def acquire(self):
        """락 획득"""
        # SET key value NX PX milliseconds
        # NX: key가 존재하지 않을 때만 설정
        # PX: 만료 시간 (밀리초)
        result = self.redis_client.set(
            self.resource_name,
            nx=True,
            px=self.ttl
        )
        return result is not None
    
    def release(self):
        """락 해제 (Lua 스크립트 사용)"""
        # lua 스크립트로 원자성 보장
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        self.redis_client.eval(lua_script, 1, self.resource_name, self.lock_value)

r = redis.Redis(host="localhost", port=6379, decode_response=True)
lock = SimpleLock(r, "lock:order:123", ttl=30000)

if lock.acquire():
    try:
        print("작업 수행 중...")
        time.sleep(5)
    finally:
        lock.release()
else:
    print("락 획득 실패")

