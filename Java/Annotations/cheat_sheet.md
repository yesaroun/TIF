# Java Annotation Cheat Sheet

## 1. Java 기본 어노테이션

| 어노테이션 | 설명 | 예시 |
|-----------|------|------|
| `@Override` | 메서드 오버라이드 명시 | `@Override public String toString()` |
| `@Deprecated` | 사용 자제 권고 | `@Deprecated(since="1.5", forRemoval=true)` |
| `@SuppressWarnings` | 컴파일러 경고 무시 | `@SuppressWarnings("unchecked")` |
| `@FunctionalInterface` | 함수형 인터페이스 검증 | 람다용 인터페이스에 사용 |
| `@SafeVarargs` | 가변인자 타입 안전 선언 | 제네릭 가변인자 메서드에 사용 |

## 2. 메타 어노테이션 (어노테이션을 위한 어노테이션)

| 어노테이션 | 설명 | 주요 값 |
|-----------|------|---------|
| `@Target` | 적용 대상 지정 | `TYPE`, `METHOD`, `FIELD`, `PARAMETER`, `CONSTRUCTOR` |
| `@Retention` | 유지 정책 | `SOURCE`, `CLASS`, `RUNTIME` |
| `@Documented` | Javadoc에 포함 | - |
| `@Inherited` | 상속 시 어노테이션 전파 | 클래스에만 적용 |
| `@Repeatable` | 반복 적용 허용 | 컨테이너 어노테이션 필요 |

## 3. Spring Core 어노테이션

### 빈 등록
| 어노테이션 | 설명 |
|-----------|------|
| `@Component` | 일반 컴포넌트 등록 |
| `@Service` | 서비스 계층 (비즈니스 로직) |
| `@Repository` | 데이터 접근 계층 (예외 변환 지원) |
| `@Controller` | 웹 컨트롤러 (뷰 반환) |
| `@RestController` | REST API 컨트롤러 (`@Controller` + `@ResponseBody`) |

### 의존성 주입
| 어노테이션 | 설명 | 예시 |
|-----------|------|------|
| `@Autowired` | 자동 의존성 주입 | 생성자, 필드, setter에 사용 |
| `@Qualifier("name")` | 빈 이름으로 주입 대상 지정 | 동일 타입 빈이 여러 개일 때 |
| `@Primary` | 기본 주입 빈 지정 | 우선순위 설정 |
| `@Value("${key}")` | 프로퍼티 값 주입 | `@Value("${server.port}")` |

### 설정
| 어노테이션 | 설명 |
|-----------|------|
| `@Configuration` | 설정 클래스 선언 |
| `@Bean` | 빈 수동 등록 (메서드에) |
| `@ComponentScan` | 컴포넌트 스캔 범위 지정 |
| `@Import` | 다른 설정 클래스 가져오기 |
| `@PropertySource` | 외부 프로퍼티 파일 로드 |

### 스코프 & 라이프사이클
| 어노테이션 | 설명 |
|-----------|------|
| `@Scope("prototype")` | 빈 스코프 지정 (`singleton`, `prototype`, `request`, `session`) |
| `@Lazy` | 지연 초기화 |
| `@PostConstruct` | 초기화 후 실행 |
| `@PreDestroy` | 소멸 전 실행 |

## 4. Spring Web 어노테이션

### 요청 매핑
| 어노테이션 | HTTP 메서드 |
|-----------|-------------|
| `@RequestMapping` | 모든 메서드 (범용) |
| `@GetMapping` | GET |
| `@PostMapping` | POST |
| `@PutMapping` | PUT |
| `@DeleteMapping` | DELETE |
| `@PatchMapping` | PATCH |

### 요청 파라미터
| 어노테이션 | 용도 | 예시 |
|-----------|------|------|
| `@PathVariable` | URL 경로 변수 | `/users/{id}` → `@PathVariable Long id` |
| `@RequestParam` | 쿼리 파라미터 | `?name=kim` → `@RequestParam String name` |
| `@RequestBody` | 요청 본문 (JSON) | POST/PUT 데이터 바인딩 |
| `@RequestHeader` | HTTP 헤더 | `@RequestHeader("Authorization")` |
| `@CookieValue` | 쿠키 값 | `@CookieValue("sessionId")` |
| `@ModelAttribute` | 폼 데이터 바인딩 | 객체로 매핑 |

### 응답 & 예외
| 어노테이션 | 설명 |
|-----------|------|
| `@ResponseBody` | 반환값을 응답 본문으로 |
| `@ResponseStatus` | HTTP 상태 코드 지정 |
| `@ExceptionHandler` | 예외 처리 메서드 |
| `@ControllerAdvice` | 전역 예외 처리 클래스 |
| `@RestControllerAdvice` | `@ControllerAdvice` + `@ResponseBody` |

## 5. Spring Data / JPA 어노테이션

### 엔티티 정의
| 어노테이션 | 설명 |
|-----------|------|
| `@Entity` | JPA 엔티티 선언 |
| `@Table(name="tb_user")` | 테이블 이름 매핑 |
| `@Id` | 기본키 지정 |
| `@GeneratedValue` | 키 생성 전략 (`IDENTITY`, `SEQUENCE`, `AUTO`) |
| `@Column` | 컬럼 매핑 (이름, nullable, length 등) |

### 관계 매핑
| 어노테이션 | 설명 | fetch 기본값 |
|-----------|------|--------------|
| `@OneToOne` | 1:1 관계 | EAGER |
| `@OneToMany` | 1:N 관계 | LAZY |
| `@ManyToOne` | N:1 관계 | EAGER |
| `@ManyToMany` | N:M 관계 | LAZY |
| `@JoinColumn` | 외래키 컬럼 지정 | - |

### 쿼리 & 트랜잭션
| 어노테이션 | 설명 |
|-----------|------|
| `@Query` | 커스텀 JPQL/네이티브 쿼리 |
| `@Modifying` | UPDATE/DELETE 쿼리 표시 |
| `@Transactional` | 트랜잭션 적용 |
| `@EnableJpaRepositories` | JPA Repository 활성화 |

## 6. 커스텀 어노테이션 만들기

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface LogExecutionTime {
    String value() default "";
}
```

**핵심 포인트:**
- `@interface`로 어노테이션 정의
- `@Retention(RUNTIME)`: 런타임에 리플렉션으로 접근 가능
- `@Target`: 적용 위치 제한
- 속성은 메서드 형태로 선언, `default`로 기본값 지정

## 7. 자주 쓰는 조합 패턴

```java
// REST API 컨트롤러
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor  // Lombok
public class UserController { }

// 서비스 레이어
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class UserService { }

// 엔티티
@Entity
@Table(name = "users")
@Getter @NoArgsConstructor(access = AccessLevel.PROTECTED)
public class User { }
```

## 8. 주의사항

- `@Autowired` 필드 주입보다 **생성자 주입** 권장
- `@Transactional`은 **public 메서드**에만 적용됨
- `@ManyToOne`의 기본 fetch가 EAGER이므로 **LAZY로 변경** 권장
- `@Data` (Lombok)는 엔티티에 사용 자제 (equals/hashCode 문제)
