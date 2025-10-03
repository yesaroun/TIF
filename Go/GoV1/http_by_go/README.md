# 🌐 직접 만드는 HTTP 서버

Go 언어의 기본 TCP 소켓만을 사용해서 HTTP 서버를 처음부터 구현하는 프로젝트입니다.

## 📚 학습 목표

이 프로젝트를 통해 다음의 CS 개념을 배웁니다:

1. **네트워크 기초** - TCP/IP 프로토콜이 어떻게 동작하는지
2. **HTTP 프로토콜** - 웹 브라우저와 서버가 어떻게 통신하는지
3. **소켓 프로그래밍** - 저수준 네트워크 프로그래밍
4. **동시성** - 여러 클라이언트를 동시에 처리하는 방법

---

## 🎯 실행 방법

```bash
# 프로그램 실행
go run main.go

# 브라우저에서 접속
# http://localhost:8080
```

터미널에 요청 로그가 실시간으로 출력됩니다!

---

## 🧠 핵심 CS 개념 설명

### 1. OSI 7계층과 TCP/IP

**OSI 7계층 모델**은 네트워크 통신을 7개 계층으로 나눈 모델입니다:

```
7. 응용 계층 (Application)    ← HTTP가 여기!
6. 표현 계층 (Presentation)
5. 세션 계층 (Session)
4. 전송 계층 (Transport)      ← TCP가 여기!
3. 네트워크 계층 (Network)     ← IP가 여기!
2. 데이터링크 계층 (Data Link)
1. 물리 계층 (Physical)
```

우리가 만든 서버는:

- **TCP (4계층)**: `net.Listen("tcp", ...)` - 신뢰성 있는 연결
- **HTTP (7계층)**: 직접 파싱 - 웹 통신 프로토콜

### 2. TCP/IP란?

**TCP (Transmission Control Protocol)**는 신뢰성 있는 데이터 전송을 보장합니다.

#### TCP의 3-way Handshake (연결 수립)

```
클라이언트                    서버
   |                        |
   |-------- SYN -------->  |  (연결 요청)
   |                        |
   |<------ SYN-ACK ------- |  (요청 승인)
   |                        |
   |-------- ACK -------->  |  (연결 확립)
   |                        |
   |==== 데이터 전송 시작 ====  |
```

코드에서 이 부분:

```go
listener, err := net.Listen("tcp", s.address) // 서버가 대기
conn, err := listener.Accept() // 클라이언트 연결 수락
```

`Accept()`가 호출되면 이미 3-way handshake가 완료된 상태입니다!

### 3. HTTP 프로토콜 구조

HTTP는 **텍스트 기반 프로토콜**입니다. 브라우저가 서버에 보내는 실제 데이터:

#### HTTP 요청 구조

```
GET /hello HTTP/1.1              ← 요청 라인 (Method Path Version)
Host: localhost:8080             ← 헤더들
User-Agent: Mozilla/5.0
Accept: text/html
                                 ← 빈 줄 (헤더 끝)
[요청 본문 - POST일 때만]
```

#### HTTP 응답 구조

```
HTTP/1.1 200 OK                  ← 상태 라인
Content-Type: text/html          ← 헤더들
Content-Length: 123
Server: MyServer/1.0
                                 ← 빈 줄 (헤더 끝)
<html>...</html>                 ← 응답 본문
```

### 4. 소켓(Socket)이란?

**소켓**은 네트워크 통신의 끝점(endpoint)입니다.

```
[애플리케이션]
      ↕
   [소켓]  ← 프로그램이 네트워크에 접근하는 창구
      ↕
   [TCP/IP]
      ↕
  [네트워크]
```

코드에서:

```go
conn, err := listener.Accept() // conn이 바로 소켓!
reader := bufio.NewReader(conn) // 소켓에서 데이터 읽기
conn.Write([]byte("Hello")) // 소켓에 데이터 쓰기
```

### 5. 블로킹(Blocking)과 동시성

#### 블로킹이란?

```go
conn, err := listener.Accept() // 👈 여기서 멈춰서 대기!
// 클라이언트가 연결할 때까지 다음 줄로 안 넘어감
```

#### 동시성 처리

하나의 클라이언트를 처리하는 동안 다른 클라이언트도 받아야 합니다:

```go
for {
conn, _ := listener.Accept()
go s.handleConnection(conn) // 👈 고루틴으로 별도 처리!
}
```

**고루틴(Goroutine)** 덕분에 1000명이 동시 접속해도 모두 처리 가능!

---

## 💡 코드 상세 분석

### 1. 서버 시작

```go
listener, err := net.Listen("tcp", "localhost:8080")
```

- `net.Listen`: TCP 서버 소켓 생성
- `localhost:8080`: IP 주소(localhost = 127.0.0.1)와 포트 번호
- **포트**: 하나의 컴퓨터에서 여러 서비스를 구분하는 번호 (0-65535)

### 2. 연결 수락

```go
conn, err := listener.Accept()
```

- 클라이언트 연결 대기 (블로킹)
- 연결되면 `conn` 객체 반환
- `conn`은 해당 클라이언트와의 전용 통신 채널

### 3. HTTP 요청 파싱

```go
requestLine, _ := reader.ReadString('\n') // "GET /hello HTTP/1.1\r\n"
parts := strings.Split(requestLine, " ") // ["GET", "/hello", "HTTP/1.1"]
```

왜 `\r\n`일까?

- `\r` (Carriage Return): 커서를 줄 맨 앞으로
- `\n` (Line Feed): 커서를 다음 줄로
- HTTP 표준은 줄바꿈으로 `\r\n` 사용 (Windows 방식)

### 4. 헤더 파싱

```go
for {
line, _ := reader.ReadString('\n')
if line == "\r\n" {  // 빈 줄이면 헤더 끝
break
}
// "Host: localhost:8080" → key="Host", value="localhost:8080"
}
```

### 5. 응답 전송

```go
conn.Write([]byte("HTTP/1.1 200 OK\r\n"))
conn.Write([]byte("Content-Type: text/html\r\n"))
conn.Write([]byte("\r\n")) // 헤더 끝
conn.Write([]byte("<html>...</html>"))
```

---

## 🔬 실험해보기

### 실험 1: 텔넷으로 직접 HTTP 요청 보내기

```bash
# 터미널에서 실행
telnet localhost 8080

# 연결되면 직접 타이핑:
GET / HTTP/1.1
Host: localhost
[엔터 두 번]
```

실제 HTTP 응답을 텍스트로 볼 수 있습니다!

### 실험 2: curl로 헤더 확인

```bash
curl -v http://localhost:8080/hello
```

`-v` 옵션으로 요청/응답 전체를 볼 수 있습니다.

### 실험 3: 동시 접속 테스트

여러 브라우저 탭으로 동시에 접속해보세요. 모두 동작하나요?
→ 고루틴 덕분에 가능합니다!

---

## 📊 일반 웹 서버와 비교

| 기능      | 우리 서버       | 실제 웹 서버 (nginx 등) |
|---------|-------------|-------------------|
| HTTP 파싱 | 직접 구현       | 고도로 최적화됨          |
| 동시 접속   | 고루틴         | 이벤트 루프, 워커 프로세스   |
| 보안      | 없음          | HTTPS, 방화벽, 인증    |
| 성능      | ~1000 req/s | ~100,000 req/s    |
| 캐싱      | 없음          | 정적 파일 캐싱          |

---

## 🚀 개선 아이디어

기본을 이해했다면 다음 기능을 추가해보세요:

### Level 1: 기본 기능

- [ ] POST 메서드 지원 (본문 읽기)
- [ ] 쿼리 파라미터 파싱 (`/search?q=hello`)
- [ ] JSON 응답 지원

### Level 2: 실용 기능

- [ ] 정적 파일 서빙 (HTML, CSS, JS 파일)
- [ ] 로그를 파일로 저장
- [ ] 요청/응답 시간 측정

### Level 3: 고급 기능

- [ ] Keep-Alive 연결 (HTTP/1.1)
- [ ] 청크 전송 인코딩
- [ ] 간단한 미들웨어 시스템
- [ ] Rate Limiting

### Level 4: 도전 과제

- [ ] HTTPS 지원 (TLS)
- [ ] HTTP/2 프로토콜
- [ ] WebSocket 지원

---

## 🐛 디버깅 팁

### 서버가 시작 안 될 때

```bash
# 포트가 이미 사용 중인지 확인
lsof -i :8080  # Mac/Linux
netstat -ano | findstr :8080  # Windows

# 해당 프로세스 종료
kill -9 [PID]
```

### 요청이 파싱 안 될 때

```go
// 디버깅 코드 추가
fmt.Printf("받은 데이터: %q\n", requestLine)
fmt.Printf("파싱 결과: %+v\n", parts)
```

### 응답이 안 보일 때

브라우저 개발자 도구 (F12) → Network 탭에서 요청/응답 확인

---

## 📖 더 공부할 자료

- RFC 2616: HTTP/1.1 명세서 (공식 표준 문서)
- RFC 793: TCP 명세서
- "Computer Networking: A Top-Down Approach" 책
- Wireshark로 패킷 직접 분석해보기

---

## 🎓 퀴즈로 복습하기

1. TCP와 UDP의 차이는?
2. HTTP는 상태를 유지할까요? (Stateful vs Stateless)
3. 포트 번호는 왜 필요할까요?
4. Keep-Alive가 없으면 어떻게 될까요?
5. HTTP/1.1과 HTTP/2의 차이는?

---

## 🙏 다음 단계

이 서버를 이해했다면:

1. **HTTPS 서버 만들기** (TLS/SSL 학습)
2. **프록시 서버 만들기** (중간자 역할)
3. **간단한 데이터베이스 만들기** (파일 I/O 학습)

축하합니다! 이제 웹이 어떻게 동작하는지 깊이 이해하게 되었습니다! 🎉