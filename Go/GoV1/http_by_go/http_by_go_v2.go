package main

// HTTPRequest는 HTTP 요청을 파싱한 결과를 담습니다.
type HTTPRequest struct {
	Method  string            // GET, POST 등
	Path    string            // /hello, /about 등
	Version string            // HTTP/1.1
	Headers map[string]string // Host, User-Aget 등
	Body    string            // 요청 본문
}

// HTTPResponse는 HTTP 응답을 나타냅니다.
type HTTPResponse struct {
	StatusCode int
	StatusText string
	Headers    map[string]string
	Body       string
}

type Server struct {
	address string
	routes  map[string]func(request *HTTPRequest) *HTTPResponse
}

func NewServer(address string) *Server {
	return &Server{
		address: address,
		routes:  make(map[string]func(*HTTPRequest) *HTTPResponse),
	}
}

// HandleFunc는 특정 경로에 대한 핸들러를 등록합니다.
func (s *Server) HandleFunc(path string, handler func(request *HTTPRequest) *HTTPResponse) {
	s.routes[path] = handler
}

func main() {
	// 서버 생성
	server := NewServer("localhost:8080")
}
