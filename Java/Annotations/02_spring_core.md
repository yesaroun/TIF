# Spring Core 어노테이션

## 개요

Spring Framework는 어노테이션 기반으로 동작한다. XML 설정 대신 어노테이션으로 빈을 등록하고 의존성을 주입한다.

## 1. 컴포넌트 스캔과 빈 등록

### @Component

Spring이 관리하는 빈으로 등록한다. 컴포넌트 스캔 대상이 된다.

```java
@Component
public class EmailValidator {
    public boolean isValid(String email) {
        return email != null && email.contains("@");
    }
}
```

### @Component의 스테레오타입들

특정 레이어를 나타내는 특화된 어노테이션. 내부적으로 `@Component`를 포함한다.

```java
// 서비스 계층 - 비즈니스 로직
@Service
public class UserService {
    // ...
}

// 데이터 접근 계층 - DB 예외를 Spring 예외로 변환
@Repository
public class UserRepository {
    // ...
}

// 웹 컨트롤러 - 뷰 반환
@Controller
public class UserController {
    // ...
}

// REST 컨트롤러 - JSON 반환
@RestController  // = @Controller + @ResponseBody
public class UserApiController {
    // ...
}
```

**왜 구분하나?**
- 코드의 역할을 명확히 표현
- `@Repository`는 데이터 접근 예외를 `DataAccessException`으로 변환
- AOP 적용 시 특정 레이어만 선택 가능

### @ComponentScan

컴포넌트를 스캔할 패키지를 지정한다.

```java
@Configuration
@ComponentScan(basePackages = "com.example.myapp")
public class AppConfig { }

// 여러 패키지 스캔
@ComponentScan(basePackages = {"com.example.service", "com.example.repository"})

// 특정 클래스 기준으로 스캔
@ComponentScan(basePackageClasses = {UserService.class, OrderService.class})

// 필터로 제외
@ComponentScan(
    basePackages = "com.example",
    excludeFilters = @ComponentScan.Filter(type = FilterType.REGEX, pattern = ".*Test.*")
)
```

## 2. 의존성 주입 (DI)

### @Autowired

자동으로 의존성을 주입한다.

```java
@Service
public class UserService {

    // 방법 1: 필드 주입 (권장하지 않음)
    @Autowired
    private UserRepository userRepository;

    // 방법 2: setter 주입
    private EmailService emailService;

    @Autowired
    public void setEmailService(EmailService emailService) {
        this.emailService = emailService;
    }

    // 방법 3: 생성자 주입 (권장!)
    private final PasswordEncoder passwordEncoder;

    @Autowired  // 생성자가 하나면 생략 가능 (Spring 4.3+)
    public UserService(PasswordEncoder passwordEncoder) {
        this.passwordEncoder = passwordEncoder;
    }
}
```

**생성자 주입을 권장하는 이유:**
- 불변성 보장 (`final` 사용 가능)
- 순환 참조 컴파일 시점에 발견
- 테스트 시 목 객체 주입 용이
- 필수 의존성 누락 방지

### @Qualifier

동일한 타입의 빈이 여러 개일 때 이름으로 지정한다.

```java
public interface MessageSender {
    void send(String message);
}

@Component("emailSender")
public class EmailSender implements MessageSender { }

@Component("smsSender")
public class SmsSender implements MessageSender { }
```

```java
@Service
public class NotificationService {

    private final MessageSender sender;

    public NotificationService(@Qualifier("emailSender") MessageSender sender) {
        this.sender = sender;
    }
}
```

### @Primary

여러 빈 중 기본으로 사용할 빈을 지정한다.

```java
@Primary
@Component
public class EmailSender implements MessageSender { }

@Component
public class SmsSender implements MessageSender { }
```

```java
@Service
public class NotificationService {
    // @Qualifier 없이도 EmailSender가 주입됨
    public NotificationService(MessageSender sender) { }
}
```

### @Value

프로퍼티 값을 주입한다.

```properties
# application.properties
app.name=MyApplication
app.timeout=30
app.features.enabled=true
```

```java
@Component
public class AppConfig {

    @Value("${app.name}")
    private String appName;

    @Value("${app.timeout:60}")  // 기본값 60
    private int timeout;

    @Value("${app.features.enabled}")
    private boolean featuresEnabled;

    // SpEL 표현식
    @Value("#{systemProperties['java.version']}")
    private String javaVersion;

    @Value("${app.servers:localhost,backup}")  // 리스트
    private String[] servers;
}
```

## 3. 설정 클래스

### @Configuration

스프링 설정 클래스를 선언한다. 내부적으로 `@Component`를 포함.

```java
@Configuration
public class AppConfig {
    // 빈 정의
}
```

### @Bean

메서드의 반환 객체를 빈으로 등록한다. 외부 라이브러리나 세밀한 설정이 필요할 때 사용.

```java
@Configuration
public class DataSourceConfig {

    @Bean
    public DataSource dataSource() {
        HikariDataSource ds = new HikariDataSource();
        ds.setJdbcUrl("jdbc:mysql://localhost/mydb");
        ds.setUsername("root");
        ds.setPassword("password");
        return ds;
    }

    @Bean
    public JdbcTemplate jdbcTemplate(DataSource dataSource) {
        return new JdbcTemplate(dataSource);  // 다른 빈 주입
    }
}
```

**@Bean 속성:**

```java
@Bean(name = "mainDataSource")  // 빈 이름 지정
@Bean(initMethod = "init", destroyMethod = "cleanup")  // 라이프사이클 메서드
public DataSource dataSource() { }
```

### @Import

다른 설정 클래스를 가져온다.

```java
@Configuration
@Import({DatabaseConfig.class, SecurityConfig.class})
public class AppConfig { }
```

### @PropertySource

외부 프로퍼티 파일을 로드한다.

```java
@Configuration
@PropertySource("classpath:custom.properties")
@PropertySource("classpath:database.properties")
public class AppConfig { }

// 또는 한 번에
@PropertySources({
    @PropertySource("classpath:custom.properties"),
    @PropertySource("classpath:database.properties")
})
```

## 4. 빈 스코프와 라이프사이클

### @Scope

빈의 스코프(생명주기 범위)를 지정한다.

```java
// 싱글톤 (기본값) - 애플리케이션에 하나
@Component
@Scope("singleton")
public class SingletonBean { }

// 프로토타입 - 요청할 때마다 새로 생성
@Component
@Scope("prototype")
public class PrototypeBean { }

// 웹 스코프
@Component
@Scope(value = "request", proxyMode = ScopedProxyMode.TARGET_CLASS)
public class RequestScopedBean { }  // HTTP 요청마다 새로 생성

@Component
@Scope(value = "session", proxyMode = ScopedProxyMode.TARGET_CLASS)
public class SessionScopedBean { }  // HTTP 세션마다 새로 생성
```

### @Lazy

빈 초기화를 지연시킨다. 처음 사용할 때 초기화.

```java
@Component
@Lazy
public class HeavyComponent {
    public HeavyComponent() {
        // 무거운 초기화 작업
    }
}

// 주입받는 쪽에서도 @Lazy 필요
@Service
public class UserService {
    @Lazy
    @Autowired
    private HeavyComponent heavyComponent;
}
```

### @PostConstruct / @PreDestroy

빈 라이프사이클 콜백 메서드를 지정한다.

```java
@Component
public class DatabaseConnection {

    private Connection connection;

    @PostConstruct  // 의존성 주입 완료 후 실행
    public void init() {
        System.out.println("Initializing database connection...");
        connection = createConnection();
    }

    @PreDestroy  // 빈 소멸 전 실행
    public void cleanup() {
        System.out.println("Closing database connection...");
        if (connection != null) {
            connection.close();
        }
    }
}
```

**실행 순서:**
1. 생성자 호출
2. 의존성 주입 (@Autowired)
3. @PostConstruct 메서드
4. ... (빈 사용) ...
5. @PreDestroy 메서드
6. 빈 소멸

## 5. 프로파일

### @Profile

특정 환경에서만 빈을 활성화한다.

```java
@Configuration
@Profile("dev")
public class DevConfig {
    @Bean
    public DataSource dataSource() {
        // H2 인메모리 DB
    }
}

@Configuration
@Profile("prod")
public class ProdConfig {
    @Bean
    public DataSource dataSource() {
        // MySQL 프로덕션 DB
    }
}
```

```java
// 여러 프로파일
@Profile({"dev", "test"})

// NOT 연산
@Profile("!prod")

// AND 연산
@Profile({"cloud", "kubernetes"})  // cloud AND kubernetes
```

**프로파일 활성화:**
```properties
# application.properties
spring.profiles.active=dev
```

## 6. 조건부 빈 등록

### @Conditional

조건에 따라 빈 등록 여부를 결정한다.

```java
public class OnLinuxCondition implements Condition {
    @Override
    public boolean matches(ConditionContext context, AnnotatedTypeMetadata metadata) {
        return context.getEnvironment().getProperty("os.name").contains("Linux");
    }
}

@Configuration
public class OsConfig {

    @Bean
    @Conditional(OnLinuxCondition.class)
    public FileService linuxFileService() {
        return new LinuxFileService();
    }
}
```

**Spring Boot의 조건 어노테이션:**

```java
@ConditionalOnProperty(name = "feature.enabled", havingValue = "true")
@ConditionalOnClass(DataSource.class)
@ConditionalOnMissingBean(DataSource.class)
@ConditionalOnWebApplication
```

## 7. 실전 예제

```java
@Configuration
@ComponentScan(basePackages = "com.example")
@PropertySource("classpath:application.properties")
public class AppConfig {

    @Value("${db.url}")
    private String dbUrl;

    @Bean
    @Profile("dev")
    public DataSource devDataSource() {
        return new EmbeddedDatabaseBuilder()
            .setType(EmbeddedDatabaseType.H2)
            .build();
    }

    @Bean
    @Profile("prod")
    public DataSource prodDataSource() {
        HikariDataSource ds = new HikariDataSource();
        ds.setJdbcUrl(dbUrl);
        return ds;
    }
}

@Service
@RequiredArgsConstructor  // Lombok - 생성자 주입 자동 생성
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @PostConstruct
    public void init() {
        log.info("UserService initialized");
    }

    public User createUser(String email, String password) {
        String encoded = passwordEncoder.encode(password);
        return userRepository.save(new User(email, encoded));
    }
}
```

## 정리

| 어노테이션 | 용도 |
|-----------|------|
| `@Component` | 빈 등록 (범용) |
| `@Service` | 서비스 레이어 빈 |
| `@Repository` | 데이터 접근 레이어 빈 |
| `@Controller` | 웹 컨트롤러 빈 |
| `@Configuration` | 설정 클래스 |
| `@Bean` | 메서드로 빈 등록 |
| `@Autowired` | 의존성 자동 주입 |
| `@Qualifier` | 빈 이름으로 지정 |
| `@Primary` | 기본 빈 지정 |
| `@Value` | 프로퍼티 값 주입 |
| `@Scope` | 빈 스코프 지정 |
| `@Lazy` | 지연 초기화 |
| `@PostConstruct` | 초기화 후 실행 |
| `@PreDestroy` | 소멸 전 실행 |
| `@Profile` | 환경별 빈 활성화 |
