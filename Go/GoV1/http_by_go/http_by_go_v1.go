package main

import (
	"bufio"
	"fmt"
	"log"
	"net"
	"strings"
	"time"
)

// HTTPRequest는 HTTP 요청을 파싱한 결과를 담습니다
type HTTPRequest struct {
	Method  string            // GET, POST 등
	Path    string            // /hello, /about 등
	Version string            // HTTP/1.1
	Headers map[string]string // Host, User-Agent 등
	Body    string            // 요청 본문
}

// HTTPResponse는 HTTP 응답을 나타냅니다
type HTTPResponse struct {
	StatusCode int
	StatusText string
	Headers    map[string]string
	Body       string
}

// Server는 우리가 만든 HTTP 서버입니다
type Server struct {
	address string
	routes  map[string]func(*HTTPRequest) *HTTPResponse
}

// NewServer는 새로운 서버를 생성합니다
func NewServer(address string) *Server {
	return &Server{
		address: address,
		routes:  make(map[string]func(*HTTPRequest) *HTTPResponse),
	}
}

// HandleFunc는 특정 경로에 대한 핸들러를 등록합니다
func (s *Server) HandleFunc(path string, handler func(*HTTPRequest) *HTTPResponse) {
	s.routes[path] = handler
}

// Start는 서버를 시작합니다
func (s *Server) Start() error {
	// TCP 리스너 생성 (클라이언트 연결을 기다림)
	listener, err := net.Listen("tcp", s.address)
	if err != nil {
		return fmt.Errorf("리스너 생성 실패: %v", err)
	}
	defer listener.Close()

	fmt.Printf("🚀 서버가 %s 에서 시작되었습니다!\n", s.address)
	fmt.Printf("📡 브라우저에서 http://localhost:8080 접속해보세요\n\n")

	// 무한 루프: 계속 클라이언트 연결을 받습니다
	for {
		// 클라이언트 연결을 기다립니다 (블로킹)
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("연결 수락 실패: %v", err)
			continue
		}

		// 각 클라이언트를 별도 고루틴에서 처리 (동시 처리)
		go s.handleConnection(conn)
	}
}

// handleConnection은 클라이언트 연결을 처리합니다
func (s *Server) handleConnection(conn net.Conn) {
	defer conn.Close()

	// 연결 시간 제한 설정 (30초)
	conn.SetDeadline(time.Now().Add(30 * time.Second))

	// HTTP 요청 읽기
	request, err := s.parseRequest(conn)
	if err != nil {
		log.Printf("❌ 요청 파싱 실패: %v", err)
		return
	}

	// 요청 정보 출력
	fmt.Printf("📥 [%s] %s %s\n", time.Now().Format("15:04:05"), request.Method, request.Path)

	// 라우팅: 경로에 맞는 핸들러 찾기
	var response *HTTPResponse
	if handler, exists := s.routes[request.Path]; exists {
		response = handler(request)
	} else {
		response = &HTTPResponse{
			StatusCode: 404,
			StatusText: "Not Found",
			Body:       "<h1>404 - 페이지를 찾을 수 없습니다</h1>",
		}
	}

	// 응답 헤더가 없으면 기본값 설정
	if response.Headers == nil {
		response.Headers = make(map[string]string)
	}
	response.Headers["Content-Type"] = "text/html; charset=utf-8"
	response.Headers["Content-Length"] = fmt.Sprintf("%d", len(response.Body))
	response.Headers["Server"] = "MySimpleHTTPServer/1.0"

	// HTTP 응답 전송
	s.sendResponse(conn, response)
}

// parseRequest는 TCP 연결에서 HTTP 요청을 읽어서 파싱합니다
func (s *Server) parseRequest(conn net.Conn) (*HTTPRequest, error) {
	reader := bufio.NewReader(conn)

	// 첫 번째 줄 읽기: "GET /hello HTTP/1.1"
	requestLine, err := reader.ReadString('\n')
	if err != nil {
		return nil, err
	}
	requestLine = strings.TrimSpace(requestLine)

	// 요청 라인 파싱
	parts := strings.Split(requestLine, " ")
	if len(parts) != 3 {
		return nil, fmt.Errorf("잘못된 요청 라인: %s", requestLine)
	}

	request := &HTTPRequest{
		Method:  parts[0],
		Path:    parts[1],
		Version: parts[2],
		Headers: make(map[string]string),
	}

	// 헤더 읽기
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			return nil, err
		}
		line = strings.TrimSpace(line)

		// 빈 줄이면 헤더 끝
		if line == "" {
			break
		}

		// 헤더 파싱: "Host: localhost:8080"
		colonIndex := strings.Index(line, ":")
		if colonIndex > 0 {
			key := strings.TrimSpace(line[:colonIndex])
			value := strings.TrimSpace(line[colonIndex+1:])
			request.Headers[key] = value
		}
	}

	return request, nil
}

// sendResponse는 HTTP 응답을 클라이언트에게 전송합니다
func (s *Server) sendResponse(conn net.Conn, response *HTTPResponse) {
	// 상태 라인 작성
	statusLine := fmt.Sprintf("HTTP/1.1 %d %s\r\n", response.StatusCode, response.StatusText)
	conn.Write([]byte(statusLine))

	// 헤더 작성
	for key, value := range response.Headers {
		headerLine := fmt.Sprintf("%s: %s\r\n", key, value)
		conn.Write([]byte(headerLine))
	}

	// 빈 줄 (헤더와 본문 구분)
	conn.Write([]byte("\r\n"))

	// 본문 작성
	conn.Write([]byte(response.Body))

	fmt.Printf("📤 [%s] 응답 전송: %d %s\n", time.Now().Format("15:04:05"), response.StatusCode, response.StatusText)
}

func main() {
	// 서버 생성
	server := NewServer("localhost:8080")

	// 라우트 등록
	server.HandleFunc("/", func(req *HTTPRequest) *HTTPResponse {
		html := `
<!DOCTYPE html>
<html>
<head>
    <title>홈페이지</title>
    <style>
        body { font-family: Arial; padding: 50px; background: #f0f0f0; }
        .container { background: white; padding: 30px; border-radius: 10px; }
        h1 { color: #333; }
        a { color: #0066cc; text-decoration: none; margin: 0 10px; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎉 직접 만든 HTTP 서버입니다!</h1>
        <p>Go와 TCP 소켓만으로 만들어졌어요.</p>
        <hr>
        <p>다른 페이지도 방문해보세요:</p>
        <a href="/hello">인사 페이지</a>
        <a href="/time">현재 시간</a>
        <a href="/about">소개 페이지</a>
    </div>
</body>
</html>
`
		return &HTTPResponse{
			StatusCode: 200,
			StatusText: "OK",
			Body:       html,
		}
	})

	server.HandleFunc("/hello", func(req *HTTPRequest) *HTTPResponse {
		return &HTTPResponse{
			StatusCode: 200,
			StatusText: "OK",
			Body:       "<h1>안녕하세요! 👋</h1><p><a href='/'>홈으로 돌아가기</a></p>",
		}
	})

	server.HandleFunc("/time", func(req *HTTPRequest) *HTTPResponse {
		currentTime := time.Now().Format("2006-01-02 15:04:05")
		html := fmt.Sprintf("<h1>⏰ 현재 시간</h1><p>%s</p><p><a href='/'>홈으로 돌아가기</a></p>", currentTime)
		return &HTTPResponse{
			StatusCode: 200,
			StatusText: "OK",
			Body:       html,
		}
	})

	server.HandleFunc("/about", func(req *HTTPRequest) *HTTPResponse {
		html := `
<h1>📚 이 서버에 대해</h1>
<p>이 서버는 Go의 net 패키지만을 사용하여 직접 구현했습니다.</p>
<ul>
    <li>TCP 소켓 직접 다루기</li>
    <li>HTTP 프로토콜 파싱</li>
    <li>동시 연결 처리 (goroutine)</li>
</ul>
<p><a href='/'>홈으로 돌아가기</a></p>
`
		return &HTTPResponse{
			StatusCode: 200,
			StatusText: "OK",
			Body:       html,
		}
	})

	// 서버 시작
	if err := server.Start(); err != nil {
		log.Fatalf("서버 시작 실패: %v", err)
	}
}
