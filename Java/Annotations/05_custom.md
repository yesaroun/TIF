# 커스텀 어노테이션 만들기

## 개요

직접 어노테이션을 정의하고, 리플렉션이나 Spring AOP로 처리하는 방법을 다룬다.

## 1. 어노테이션 정의 기본

### 기본 구조

```java
import java.lang.annotation.*;

@Target(ElementType.METHOD)         // 적용 대상
@Retention(RetentionPolicy.RUNTIME) // 유지 정책
public @interface MyAnnotation {
    String value() default "";      // 요소 정의
}
```

### 메타 어노테이션

| 어노테이션 | 설명 |
|-----------|------|
| `@Target` | 어노테이션 적용 위치 |
| `@Retention` | 어노테이션 유지 범위 |
| `@Documented` | Javadoc에 포함 |
| `@Inherited` | 자식 클래스에 상속 |
| `@Repeatable` | 반복 적용 허용 |

### 요소(Element) 정의

```java
public @interface Task {
    // 기본 타입
    String name();
    int priority() default 0;
    boolean active() default true;

    // 배열
    String[] tags() default {};

    // Enum
    TaskType type() default TaskType.NORMAL;

    // Class
    Class<?> handler() default Void.class;

    // 다른 어노테이션
    Deprecated deprecated() default @Deprecated;
}

public enum TaskType {
    NORMAL, URGENT, LOW
}
```

**사용:**
```java
@Task(name = "process", priority = 1, tags = {"async", "batch"})
public void processData() { }
```

## 2. 리플렉션으로 어노테이션 처리

### 기본 리플렉션

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface Test {
    String description() default "";
}

public class TestRunner {
    public static void main(String[] args) throws Exception {
        Class<?> clazz = MyTests.class;

        for (Method method : clazz.getDeclaredMethods()) {
            if (method.isAnnotationPresent(Test.class)) {
                Test test = method.getAnnotation(Test.class);
                System.out.println("Running: " + method.getName());
                System.out.println("Description: " + test.description());

                try {
                    method.invoke(clazz.getDeclaredConstructor().newInstance());
                    System.out.println("PASSED");
                } catch (Exception e) {
                    System.out.println("FAILED: " + e.getCause().getMessage());
                }
            }
        }
    }
}

class MyTests {
    @Test(description = "숫자 더하기 테스트")
    public void testAdd() {
        assert 1 + 1 == 2;
    }

    @Test(description = "숫자 빼기 테스트")
    public void testSubtract() {
        assert 5 - 3 == 2;
    }
}
```

### 필드 어노테이션 처리

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.FIELD)
public @interface Validate {
    int min() default 0;
    int max() default Integer.MAX_VALUE;
    boolean notNull() default false;
}

public class Validator {
    public static void validate(Object obj) throws Exception {
        Class<?> clazz = obj.getClass();

        for (Field field : clazz.getDeclaredFields()) {
            if (field.isAnnotationPresent(Validate.class)) {
                Validate v = field.getAnnotation(Validate.class);
                field.setAccessible(true);
                Object value = field.get(obj);

                // null 체크
                if (v.notNull() && value == null) {
                    throw new IllegalArgumentException(field.getName() + " cannot be null");
                }

                // 범위 체크 (숫자인 경우)
                if (value instanceof Number) {
                    int num = ((Number) value).intValue();
                    if (num < v.min() || num > v.max()) {
                        throw new IllegalArgumentException(
                            field.getName() + " must be between " + v.min() + " and " + v.max()
                        );
                    }
                }
            }
        }
    }
}

public class User {
    @Validate(notNull = true)
    private String name;

    @Validate(min = 0, max = 150)
    private int age;
}
```

## 3. Spring AOP와 함께 사용

### 실행 시간 측정 어노테이션

**1단계: 어노테이션 정의**
```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface LogExecutionTime {
}
```

**2단계: Aspect 구현**
```java
@Aspect
@Component
public class LogExecutionTimeAspect {

    private static final Logger log = LoggerFactory.getLogger(LogExecutionTimeAspect.class);

    @Around("@annotation(LogExecutionTime)")
    public Object logExecutionTime(ProceedingJoinPoint joinPoint) throws Throwable {
        long startTime = System.currentTimeMillis();

        Object result = joinPoint.proceed();

        long endTime = System.currentTimeMillis();
        log.info("{} executed in {}ms",
            joinPoint.getSignature().getName(),
            endTime - startTime);

        return result;
    }
}
```

**3단계: 사용**
```java
@Service
public class UserService {

    @LogExecutionTime
    public List<User> findAll() {
        // 시간이 걸리는 작업
        return userRepository.findAll();
    }
}
```

### 권한 체크 어노테이션

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface RequireRole {
    String[] value();
}

@Aspect
@Component
@RequiredArgsConstructor
public class RoleCheckAspect {

    private final AuthService authService;

    @Before("@annotation(requireRole)")
    public void checkRole(JoinPoint joinPoint, RequireRole requireRole) {
        String currentRole = authService.getCurrentUserRole();
        String[] requiredRoles = requireRole.value();

        boolean hasRole = Arrays.stream(requiredRoles)
            .anyMatch(role -> role.equals(currentRole));

        if (!hasRole) {
            throw new AccessDeniedException("Required role: " + Arrays.toString(requiredRoles));
        }
    }
}

// 사용
@RestController
public class AdminController {

    @RequireRole({"ADMIN", "SUPER_ADMIN"})
    @GetMapping("/admin/users")
    public List<User> getAllUsers() {
        return userService.findAll();
    }
}
```

### 캐싱 어노테이션 직접 구현

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface SimpleCache {
    String key();
    int ttlSeconds() default 60;
}

@Aspect
@Component
public class SimpleCacheAspect {

    private final Map<String, CacheEntry> cache = new ConcurrentHashMap<>();

    @Around("@annotation(simpleCache)")
    public Object cache(ProceedingJoinPoint joinPoint, SimpleCache simpleCache) throws Throwable {
        String key = buildKey(simpleCache.key(), joinPoint.getArgs());

        CacheEntry entry = cache.get(key);
        if (entry != null && !entry.isExpired()) {
            return entry.getValue();
        }

        Object result = joinPoint.proceed();

        cache.put(key, new CacheEntry(result, simpleCache.ttlSeconds()));
        return result;
    }

    private String buildKey(String keyTemplate, Object[] args) {
        String key = keyTemplate;
        for (int i = 0; i < args.length; i++) {
            key = key.replace("{" + i + "}", String.valueOf(args[i]));
        }
        return key;
    }

    private static class CacheEntry {
        private final Object value;
        private final long expiresAt;

        CacheEntry(Object value, int ttlSeconds) {
            this.value = value;
            this.expiresAt = System.currentTimeMillis() + (ttlSeconds * 1000L);
        }

        boolean isExpired() { return System.currentTimeMillis() > expiresAt; }
        Object getValue() { return value; }
    }
}

// 사용
@Service
public class ProductService {

    @SimpleCache(key = "product:{0}", ttlSeconds = 300)
    public Product findById(Long id) {
        return productRepository.findById(id).orElseThrow();
    }
}
```

## 4. 메서드 파라미터 어노테이션

### 파라미터 유효성 검증

```java
@Target(ElementType.PARAMETER)
@Retention(RetentionPolicy.RUNTIME)
public @interface NotEmpty {
    String message() default "Value cannot be empty";
}

@Aspect
@Component
public class ParameterValidationAspect {

    @Before("execution(* com.example.service.*.*(..))")
    public void validateParameters(JoinPoint joinPoint) {
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        Method method = signature.getMethod();
        Object[] args = joinPoint.getArgs();
        Parameter[] parameters = method.getParameters();

        for (int i = 0; i < parameters.length; i++) {
            if (parameters[i].isAnnotationPresent(NotEmpty.class)) {
                NotEmpty annotation = parameters[i].getAnnotation(NotEmpty.class);

                if (args[i] == null ||
                    (args[i] instanceof String && ((String) args[i]).isEmpty())) {
                    throw new IllegalArgumentException(annotation.message());
                }
            }
        }
    }
}

// 사용
@Service
public class UserService {

    public User findByEmail(@NotEmpty(message = "Email is required") String email) {
        return userRepository.findByEmail(email).orElseThrow();
    }
}
```

## 5. 클래스 레벨 어노테이션

### API 버전 관리

```java
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@RequestMapping  // Spring의 @RequestMapping 상속
public @interface ApiVersion {
    String value();
}

public class ApiVersionRequestMappingHandlerMapping extends RequestMappingHandlerMapping {

    @Override
    protected RequestMappingInfo getMappingForMethod(Method method, Class<?> handlerType) {
        RequestMappingInfo info = super.getMappingForMethod(method, handlerType);
        if (info == null) return null;

        ApiVersion apiVersion = AnnotationUtils.findAnnotation(handlerType, ApiVersion.class);
        if (apiVersion != null) {
            String prefix = "/api/" + apiVersion.value();
            return RequestMappingInfo.paths(prefix).build().combine(info);
        }

        return info;
    }
}

// 사용
@RestController
@ApiVersion("v1")
@RequestMapping("/users")
public class UserControllerV1 {
    // /api/v1/users 로 매핑
}

@RestController
@ApiVersion("v2")
@RequestMapping("/users")
public class UserControllerV2 {
    // /api/v2/users 로 매핑
}
```

## 6. 반복 가능한 어노테이션

```java
// 1. 반복 가능 어노테이션
@Repeatable(Schedules.class)
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Schedule {
    String cron();
    String timezone() default "UTC";
}

// 2. 컨테이너 어노테이션
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Schedules {
    Schedule[] value();
}

// 3. 사용
public class BatchJob {

    @Schedule(cron = "0 0 9 * * MON")
    @Schedule(cron = "0 0 9 * * WED")
    @Schedule(cron = "0 0 9 * * FRI")
    public void weekdayMorningJob() {
        // 월/수/금 오전 9시에 실행
    }
}

// 4. 리플렉션으로 읽기
Method method = BatchJob.class.getMethod("weekdayMorningJob");
Schedule[] schedules = method.getAnnotationsByType(Schedule.class);

for (Schedule schedule : schedules) {
    System.out.println("Cron: " + schedule.cron());
}
```

## 7. 실전 예제: 감사 로그 어노테이션

```java
// 어노테이션 정의
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface AuditLog {
    String action();
    String entityType() default "";
}

// Aspect 구현
@Aspect
@Component
@RequiredArgsConstructor
public class AuditLogAspect {

    private final AuditLogRepository auditLogRepository;
    private final AuthService authService;

    @AfterReturning(
        pointcut = "@annotation(auditLog)",
        returning = "result"
    )
    public void logAfterSuccess(JoinPoint joinPoint, AuditLog auditLog, Object result) {
        createLog(auditLog, joinPoint, "SUCCESS", null);
    }

    @AfterThrowing(
        pointcut = "@annotation(auditLog)",
        throwing = "exception"
    )
    public void logAfterFailure(JoinPoint joinPoint, AuditLog auditLog, Exception exception) {
        createLog(auditLog, joinPoint, "FAILURE", exception.getMessage());
    }

    private void createLog(AuditLog auditLog, JoinPoint joinPoint, String status, String error) {
        AuditLogEntity log = AuditLogEntity.builder()
            .action(auditLog.action())
            .entityType(auditLog.entityType())
            .userId(authService.getCurrentUserId())
            .methodName(joinPoint.getSignature().getName())
            .parameters(Arrays.toString(joinPoint.getArgs()))
            .status(status)
            .errorMessage(error)
            .timestamp(LocalDateTime.now())
            .build();

        auditLogRepository.save(log);
    }
}

// 사용
@Service
public class OrderService {

    @AuditLog(action = "CREATE_ORDER", entityType = "Order")
    @Transactional
    public Order createOrder(OrderRequest request) {
        // 주문 생성 로직
        return orderRepository.save(order);
    }

    @AuditLog(action = "CANCEL_ORDER", entityType = "Order")
    @Transactional
    public void cancelOrder(Long orderId) {
        // 주문 취소 로직
    }
}
```

## 8. Spring의 커스텀 어노테이션 합성

```java
// 여러 어노테이션을 하나로 합성
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*")
public @interface ApiController {
    @AliasFor(annotation = RequestMapping.class, attribute = "value")
    String[] value() default {};
}

// 사용: 3개 어노테이션 효과를 하나로
@ApiController("/users")
public class UserController {
    // @RestController + @RequestMapping("/api") + @CrossOrigin 적용됨
}
```

```java
// 트랜잭션 + 읽기 전용 합성
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Transactional(readOnly = true)
public @interface ReadOnlyService {
}

@ReadOnlyService
@Service
public class ReportService {
    // 모든 메서드가 읽기 전용 트랜잭션
}
```

## 정리

| 단계 | 설명 |
|------|------|
| 1. `@interface`로 정의 | 어노테이션 선언 |
| 2. 메타 어노테이션 | `@Target`, `@Retention` 필수 |
| 3. 요소 정의 | 속성값 정의 (default 가능) |
| 4. 처리 로직 | 리플렉션 또는 AOP로 처리 |

**팁:**
- `@Retention(RUNTIME)` 필수 (런타임에 읽어야 하므로)
- Spring AOP는 프록시 기반이므로 self-invocation에서 동작 안 함
- 어노테이션 합성으로 반복 코드 줄이기
