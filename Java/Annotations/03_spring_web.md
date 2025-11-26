# Spring Web 어노테이션

## 개요

Spring MVC와 REST API 개발에 필요한 어노테이션들을 다룬다.

## 1. 컨트롤러 정의

### @Controller

뷰를 반환하는 웹 컨트롤러를 선언한다.

```java
@Controller
public class PageController {

    @GetMapping("/home")
    public String home(Model model) {
        model.addAttribute("message", "Hello");
        return "home";  // home.html 뷰 렌더링
    }
}
```

### @RestController

REST API 컨트롤러를 선언한다. `@Controller` + `@ResponseBody`와 동일.

```java
@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);  // JSON으로 반환
    }
}
```

### @ResponseBody

메서드 반환값을 HTTP 응답 본문으로 직접 반환한다.

```java
@Controller
public class MixedController {

    @GetMapping("/page")
    public String page() {
        return "page";  // 뷰 이름
    }

    @GetMapping("/data")
    @ResponseBody
    public Map<String, String> data() {
        return Map.of("key", "value");  // JSON
    }
}
```

## 2. 요청 매핑

### @RequestMapping

모든 HTTP 메서드에 대한 요청을 매핑한다.

```java
@RestController
@RequestMapping("/api/v1/products")  // 클래스 레벨: 기본 경로
public class ProductController {

    @RequestMapping(method = RequestMethod.GET)
    public List<Product> list() { }

    @RequestMapping(value = "/{id}", method = RequestMethod.GET)
    public Product get(@PathVariable Long id) { }

    // 여러 경로 매핑
    @RequestMapping(value = {"/all", "/list"}, method = RequestMethod.GET)
    public List<Product> getAll() { }

    // 여러 메서드 허용
    @RequestMapping(value = "/{id}", method = {RequestMethod.PUT, RequestMethod.PATCH})
    public Product update(@PathVariable Long id) { }
}
```

**@RequestMapping 속성:**
| 속성 | 설명 |
|------|------|
| `value` / `path` | URL 경로 |
| `method` | HTTP 메서드 |
| `params` | 필수 요청 파라미터 |
| `headers` | 필수 요청 헤더 |
| `consumes` | 요청 Content-Type |
| `produces` | 응답 Content-Type |

```java
@RequestMapping(
    value = "/upload",
    method = RequestMethod.POST,
    consumes = MediaType.MULTIPART_FORM_DATA_VALUE,
    produces = MediaType.APPLICATION_JSON_VALUE
)
public Response upload() { }
```

### HTTP 메서드별 매핑 (축약형)

```java
@GetMapping("/users")           // GET
@PostMapping("/users")          // POST
@PutMapping("/users/{id}")      // PUT
@DeleteMapping("/users/{id}")   // DELETE
@PatchMapping("/users/{id}")    // PATCH
```

```java
@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping
    public List<User> list() { }

    @GetMapping("/{id}")
    public User get(@PathVariable Long id) { }

    @PostMapping
    public User create(@RequestBody UserDto dto) { }

    @PutMapping("/{id}")
    public User update(@PathVariable Long id, @RequestBody UserDto dto) { }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) { }
}
```

## 3. 요청 데이터 바인딩

### @PathVariable

URL 경로의 변수를 추출한다.

```java
// 기본 사용
@GetMapping("/users/{id}")
public User getUser(@PathVariable Long id) { }

// 변수명이 다를 때
@GetMapping("/users/{userId}")
public User getUser(@PathVariable("userId") Long id) { }

// 여러 변수
@GetMapping("/users/{userId}/orders/{orderId}")
public Order getOrder(
    @PathVariable Long userId,
    @PathVariable Long orderId) { }

// 선택적 (required = false)
@GetMapping({"/users/{id}", "/users"})
public List<User> getUsers(@PathVariable(required = false) Long id) { }
```

### @RequestParam

쿼리 파라미터를 추출한다.

```java
// GET /users?name=kim
@GetMapping("/users")
public List<User> search(@RequestParam String name) { }

// 선택적 파라미터
@GetMapping("/users")
public List<User> search(
    @RequestParam(required = false) String name,
    @RequestParam(defaultValue = "0") int page,
    @RequestParam(defaultValue = "10") int size) { }

// 이름 지정
@GetMapping("/users")
public List<User> search(@RequestParam("q") String query) { }

// 모든 파라미터를 Map으로
@GetMapping("/search")
public List<Product> search(@RequestParam Map<String, String> params) { }

// 같은 이름의 여러 값
// GET /users?role=ADMIN&role=USER
@GetMapping("/users")
public List<User> search(@RequestParam List<String> role) { }
```

### @RequestBody

HTTP 요청 본문을 객체로 변환한다. 주로 JSON 데이터 처리.

```java
@PostMapping("/users")
public User create(@RequestBody UserCreateDto dto) {
    return userService.create(dto);
}

// 유효성 검증과 함께
@PostMapping("/users")
public User create(@Valid @RequestBody UserCreateDto dto) { }
```

```java
// DTO 클래스
public class UserCreateDto {
    @NotBlank
    private String name;

    @Email
    private String email;

    @Size(min = 8)
    private String password;

    // getters, setters
}
```

### @RequestHeader

HTTP 요청 헤더를 추출한다.

```java
@GetMapping("/info")
public String info(
    @RequestHeader("Authorization") String auth,
    @RequestHeader("User-Agent") String userAgent,
    @RequestHeader(value = "X-Custom", required = false) String custom) {
    return "OK";
}

// 모든 헤더를 Map으로
@GetMapping("/headers")
public Map<String, String> headers(@RequestHeader Map<String, String> headers) {
    return headers;
}

// HttpHeaders 타입으로
@GetMapping("/headers")
public void headers(@RequestHeader HttpHeaders headers) {
    headers.getContentType();
    headers.getAccept();
}
```

### @CookieValue

쿠키 값을 추출한다.

```java
@GetMapping("/user")
public User getUser(@CookieValue("sessionId") String sessionId) { }

@GetMapping("/settings")
public Settings getSettings(
    @CookieValue(value = "theme", defaultValue = "light") String theme) { }
```

### @ModelAttribute

폼 데이터를 객체로 바인딩한다.

```java
// HTML 폼 데이터 바인딩
@PostMapping("/register")
public String register(@ModelAttribute UserForm form) {
    // form.getName(), form.getEmail() 등 사용
    return "redirect:/success";
}

// 모든 핸들러에서 공통으로 사용할 속성
@ModelAttribute("categories")
public List<Category> categories() {
    return categoryService.findAll();  // 모든 뷰에서 사용 가능
}
```

## 4. 응답 처리

### @ResponseStatus

HTTP 응답 상태 코드를 지정한다.

```java
@PostMapping("/users")
@ResponseStatus(HttpStatus.CREATED)  // 201
public User create(@RequestBody UserDto dto) { }

@DeleteMapping("/users/{id}")
@ResponseStatus(HttpStatus.NO_CONTENT)  // 204
public void delete(@PathVariable Long id) { }
```

### ResponseEntity

상태 코드, 헤더, 본문을 세밀하게 제어한다.

```java
@GetMapping("/users/{id}")
public ResponseEntity<User> getUser(@PathVariable Long id) {
    User user = userService.findById(id);
    if (user == null) {
        return ResponseEntity.notFound().build();
    }
    return ResponseEntity.ok(user);
}

@PostMapping("/users")
public ResponseEntity<User> create(@RequestBody UserDto dto) {
    User user = userService.create(dto);
    URI location = URI.create("/api/users/" + user.getId());
    return ResponseEntity.created(location).body(user);
}

// 커스텀 헤더 추가
@GetMapping("/download")
public ResponseEntity<byte[]> download() {
    return ResponseEntity.ok()
        .header("Content-Disposition", "attachment; filename=file.pdf")
        .contentType(MediaType.APPLICATION_PDF)
        .body(fileBytes);
}
```

## 5. 예외 처리

### @ExceptionHandler

특정 예외를 처리하는 메서드를 정의한다.

```java
@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id)
            .orElseThrow(() -> new UserNotFoundException(id));
    }

    // 이 컨트롤러 내에서 발생하는 UserNotFoundException 처리
    @ExceptionHandler(UserNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ErrorResponse handleUserNotFound(UserNotFoundException e) {
        return new ErrorResponse("USER_NOT_FOUND", e.getMessage());
    }

    // 여러 예외 처리
    @ExceptionHandler({IllegalArgumentException.class, IllegalStateException.class})
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ErrorResponse handleBadRequest(RuntimeException e) {
        return new ErrorResponse("BAD_REQUEST", e.getMessage());
    }
}
```

### @ControllerAdvice / @RestControllerAdvice

전역 예외 처리 클래스를 정의한다.

```java
@RestControllerAdvice  // = @ControllerAdvice + @ResponseBody
public class GlobalExceptionHandler {

    @ExceptionHandler(UserNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ErrorResponse handleUserNotFound(UserNotFoundException e) {
        return new ErrorResponse("USER_NOT_FOUND", e.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ErrorResponse handleValidationError(MethodArgumentNotValidException e) {
        List<String> errors = e.getBindingResult()
            .getFieldErrors()
            .stream()
            .map(err -> err.getField() + ": " + err.getDefaultMessage())
            .toList();
        return new ErrorResponse("VALIDATION_ERROR", errors.toString());
    }

    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public ErrorResponse handleUnknown(Exception e) {
        log.error("Unexpected error", e);
        return new ErrorResponse("INTERNAL_ERROR", "서버 오류가 발생했습니다.");
    }
}
```

**특정 패키지만 적용:**
```java
@RestControllerAdvice(basePackages = "com.example.api")
public class ApiExceptionHandler { }

@RestControllerAdvice(assignableTypes = {UserController.class, OrderController.class})
public class SpecificExceptionHandler { }
```

## 6. CORS 설정

### @CrossOrigin

CORS(Cross-Origin Resource Sharing)를 허용한다.

```java
// 메서드 레벨
@GetMapping("/users")
@CrossOrigin(origins = "http://localhost:3000")
public List<User> list() { }

// 클래스 레벨
@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*", maxAge = 3600)
public class ApiController { }

// 상세 설정
@CrossOrigin(
    origins = {"http://localhost:3000", "https://example.com"},
    methods = {RequestMethod.GET, RequestMethod.POST},
    allowedHeaders = {"Authorization", "Content-Type"},
    exposedHeaders = {"X-Custom-Header"},
    allowCredentials = "true",
    maxAge = 3600
)
```

## 7. 비동기 처리

### @Async

메서드를 비동기로 실행한다.

```java
@Configuration
@EnableAsync
public class AsyncConfig { }

@Service
public class EmailService {

    @Async
    public void sendEmail(String to, String content) {
        // 별도 스레드에서 실행
        emailClient.send(to, content);
    }

    @Async
    public CompletableFuture<String> sendEmailAsync(String to) {
        String result = emailClient.send(to);
        return CompletableFuture.completedFuture(result);
    }
}
```

## 8. 실전 예제

```java
@RestController
@RequestMapping("/api/v1/posts")
@RequiredArgsConstructor
public class PostController {

    private final PostService postService;

    @GetMapping
    public Page<PostDto> list(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String keyword) {
        return postService.search(keyword, PageRequest.of(page, size));
    }

    @GetMapping("/{id}")
    public PostDto get(@PathVariable Long id) {
        return postService.findById(id)
            .orElseThrow(() -> new PostNotFoundException(id));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public PostDto create(
            @Valid @RequestBody PostCreateRequest request,
            @RequestHeader("Authorization") String token) {
        Long userId = tokenService.getUserId(token);
        return postService.create(userId, request);
    }

    @PutMapping("/{id}")
    public PostDto update(
            @PathVariable Long id,
            @Valid @RequestBody PostUpdateRequest request) {
        return postService.update(id, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Long id) {
        postService.delete(id);
    }
}

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(PostNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(PostNotFoundException e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(new ErrorResponse("POST_NOT_FOUND", e.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
            .map(err -> err.getField() + ": " + err.getDefaultMessage())
            .collect(Collectors.joining(", "));
        return ResponseEntity.badRequest()
            .body(new ErrorResponse("VALIDATION_ERROR", message));
    }
}
```

## 정리

| 어노테이션 | 용도 |
|-----------|------|
| `@Controller` | 뷰 반환 컨트롤러 |
| `@RestController` | REST API 컨트롤러 |
| `@RequestMapping` | 요청 매핑 (범용) |
| `@GetMapping` 등 | HTTP 메서드별 매핑 |
| `@PathVariable` | URL 경로 변수 |
| `@RequestParam` | 쿼리 파라미터 |
| `@RequestBody` | 요청 본문 (JSON) |
| `@RequestHeader` | HTTP 헤더 |
| `@ResponseBody` | 응답 본문으로 반환 |
| `@ResponseStatus` | HTTP 상태 코드 |
| `@ExceptionHandler` | 예외 처리 |
| `@ControllerAdvice` | 전역 예외 처리 |
| `@CrossOrigin` | CORS 허용 |
