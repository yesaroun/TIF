# Spring Data / JPA 어노테이션

## 개요

JPA(Java Persistence API)와 Spring Data JPA에서 사용하는 어노테이션들을 다룬다.

## 1. 엔티티 정의

### @Entity

JPA가 관리하는 엔티티 클래스를 선언한다.

```java
@Entity
public class User {
    @Id
    private Long id;
    private String name;
}
```

**규칙:**
- 기본 생성자 필수 (protected 가능)
- `final` 클래스 불가
- `@Id` 필수

### @Table

테이블 이름과 속성을 지정한다.

```java
@Entity
@Table(
    name = "tb_user",
    schema = "myapp",
    uniqueConstraints = @UniqueConstraint(columnNames = {"email"}),
    indexes = @Index(columnList = "created_at DESC")
)
public class User { }
```

### @Id

기본키(Primary Key)를 지정한다.

```java
@Entity
public class User {
    @Id
    private Long id;
}
```

### @GeneratedValue

기본키 생성 전략을 지정한다.

```java
// AUTO: JPA가 DB에 맞게 자동 선택 (기본값)
@Id
@GeneratedValue(strategy = GenerationType.AUTO)
private Long id;

// IDENTITY: DB의 auto_increment 사용 (MySQL, PostgreSQL)
@Id
@GeneratedValue(strategy = GenerationType.IDENTITY)
private Long id;

// SEQUENCE: 시퀀스 사용 (Oracle, PostgreSQL)
@Id
@GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "user_seq")
@SequenceGenerator(name = "user_seq", sequenceName = "user_sequence", allocationSize = 50)
private Long id;

// TABLE: 키 생성 전용 테이블 사용 (모든 DB)
@Id
@GeneratedValue(strategy = GenerationType.TABLE, generator = "user_gen")
@TableGenerator(name = "user_gen", table = "id_generator", pkColumnValue = "user_id")
private Long id;
```

**전략 선택:**
- MySQL: `IDENTITY`
- PostgreSQL: `SEQUENCE` 또는 `IDENTITY`
- Oracle: `SEQUENCE`

### @Column

컬럼 매핑을 세부 설정한다.

```java
@Entity
public class User {

    @Column(name = "user_name", nullable = false, length = 100)
    private String name;

    @Column(unique = true)
    private String email;

    @Column(precision = 10, scale = 2)  // DECIMAL(10,2)
    private BigDecimal salary;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(insertable = false, updatable = false)  // INSERT, UPDATE 제외
    private LocalDateTime createdAt;
}
```

**@Column 속성:**
| 속성 | 설명 | 기본값 |
|------|------|--------|
| `name` | 컬럼 이름 | 필드명 |
| `nullable` | NULL 허용 | true |
| `unique` | 유니크 제약 | false |
| `length` | 문자열 길이 | 255 |
| `precision` | 숫자 전체 자릿수 | 0 |
| `scale` | 소수점 자릿수 | 0 |

### @Enumerated

Enum 타입 매핑 방식을 지정한다.

```java
public enum Status {
    ACTIVE, INACTIVE, DELETED
}

@Entity
public class User {
    // ORDINAL: 순서값 저장 (0, 1, 2) - 권장하지 않음
    @Enumerated(EnumType.ORDINAL)
    private Status status1;

    // STRING: 문자열 저장 ("ACTIVE", "INACTIVE") - 권장!
    @Enumerated(EnumType.STRING)
    private Status status;
}
```

**STRING을 권장하는 이유:** Enum에 값이 추가/삭제되면 ORDINAL 순서가 바뀌어 데이터 정합성이 깨짐.

### @Temporal

날짜/시간 타입 매핑 (Java 8 이전 Date 타입용).

```java
@Temporal(TemporalType.DATE)      // 날짜만 (2024-01-15)
private Date birthDate;

@Temporal(TemporalType.TIME)      // 시간만 (10:30:00)
private Date startTime;

@Temporal(TemporalType.TIMESTAMP) // 날짜+시간
private Date createdAt;
```

**Java 8 이후는 그냥 사용:**
```java
private LocalDate birthDate;      // DATE
private LocalTime startTime;      // TIME
private LocalDateTime createdAt;  // TIMESTAMP
```

### @Lob

대용량 데이터(BLOB, CLOB)를 매핑한다.

```java
@Lob
private String content;  // CLOB

@Lob
private byte[] image;    // BLOB
```

### @Transient

영속성 컨텍스트에서 제외한다. DB에 저장하지 않음.

```java
@Entity
public class User {
    private String firstName;
    private String lastName;

    @Transient
    private String fullName;  // DB 저장 안 함

    public String getFullName() {
        return firstName + " " + lastName;
    }
}
```

## 2. 관계 매핑

### @OneToOne

1:1 관계를 매핑한다.

```java
// 양방향 1:1
@Entity
public class User {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "profile_id")  // FK 지정
    private Profile profile;
}

@Entity
public class Profile {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(mappedBy = "profile")  // 연관관계 주인 지정
    private User user;
}
```

### @OneToMany / @ManyToOne

1:N, N:1 관계를 매핑한다.

```java
@Entity
public class Team {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;

    @OneToMany(mappedBy = "team", cascade = CascadeType.ALL)
    private List<Member> members = new ArrayList<>();

    // 연관관계 편의 메서드
    public void addMember(Member member) {
        members.add(member);
        member.setTeam(this);
    }
}

@Entity
public class Member {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;

    @ManyToOne(fetch = FetchType.LAZY)  // LAZY 권장!
    @JoinColumn(name = "team_id")
    private Team team;
}
```

**기본 fetch 전략:**
- `@OneToMany`: LAZY
- `@ManyToOne`: **EAGER** → LAZY로 변경 권장!

### @ManyToMany

N:M 관계를 매핑한다.

```java
@Entity
public class Student {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToMany
    @JoinTable(
        name = "student_course",
        joinColumns = @JoinColumn(name = "student_id"),
        inverseJoinColumns = @JoinColumn(name = "course_id")
    )
    private Set<Course> courses = new HashSet<>();
}

@Entity
public class Course {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToMany(mappedBy = "courses")
    private Set<Student> students = new HashSet<>();
}
```

**실무 권장:** `@ManyToMany` 대신 중간 엔티티를 만들어 `@OneToMany` + `@ManyToOne`으로 풀기
```java
// 중간 엔티티로 변경
@Entity
public class Enrollment {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    private Student student;

    @ManyToOne(fetch = FetchType.LAZY)
    private Course course;

    private LocalDate enrolledAt;  // 추가 필드 가능!
    private String grade;
}
```

### @JoinColumn

외래키 컬럼을 지정한다.

```java
@ManyToOne
@JoinColumn(
    name = "team_id",              // FK 컬럼명
    referencedColumnName = "id",   // 참조 대상 컬럼
    nullable = false,
    foreignKey = @ForeignKey(name = "fk_member_team")
)
private Team team;
```

### Cascade 옵션

부모 엔티티의 상태 변화를 자식에게 전파한다.

```java
@OneToMany(mappedBy = "parent", cascade = CascadeType.ALL)
private List<Child> children;
```

| 타입 | 설명 |
|------|------|
| `PERSIST` | 저장 시 함께 저장 |
| `REMOVE` | 삭제 시 함께 삭제 |
| `MERGE` | 병합 시 함께 병합 |
| `REFRESH` | 새로고침 시 함께 새로고침 |
| `DETACH` | 분리 시 함께 분리 |
| `ALL` | 모든 연산 전파 |

### orphanRemoval

고아 객체(부모와 연결이 끊긴 자식)를 자동 삭제한다.

```java
@OneToMany(mappedBy = "parent", orphanRemoval = true)
private List<Child> children;

// 사용
parent.getChildren().remove(0);  // 자동으로 DELETE 쿼리 발생
```

## 3. 임베디드 타입

### @Embeddable / @Embedded

값 타입을 별도 클래스로 분리한다.

```java
@Embeddable
public class Address {
    private String city;
    private String street;
    private String zipcode;
}

@Entity
public class User {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Embedded
    private Address homeAddress;

    @Embedded
    @AttributeOverrides({
        @AttributeOverride(name = "city", column = @Column(name = "work_city")),
        @AttributeOverride(name = "street", column = @Column(name = "work_street")),
        @AttributeOverride(name = "zipcode", column = @Column(name = "work_zipcode"))
    })
    private Address workAddress;
}
```

## 4. 상속 매핑

### @Inheritance

상속 전략을 지정한다.

```java
// SINGLE_TABLE: 단일 테이블 (기본값, 성능 좋음)
@Entity
@Inheritance(strategy = InheritanceType.SINGLE_TABLE)
@DiscriminatorColumn(name = "type")
public abstract class Item {
    @Id @GeneratedValue
    private Long id;
    private String name;
}

@Entity
@DiscriminatorValue("BOOK")
public class Book extends Item {
    private String author;
}

@Entity
@DiscriminatorValue("MOVIE")
public class Movie extends Item {
    private String director;
}
```

```java
// JOINED: 조인 테이블 (정규화)
@Inheritance(strategy = InheritanceType.JOINED)

// TABLE_PER_CLASS: 구현 클래스마다 테이블 (비추천)
@Inheritance(strategy = InheritanceType.TABLE_PER_CLASS)
```

### @MappedSuperclass

공통 필드만 상속하고 테이블은 공유하지 않는다.

```java
@MappedSuperclass
public abstract class BaseEntity {
    @CreatedDate
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;
}

@Entity
public class User extends BaseEntity {
    @Id @GeneratedValue
    private Long id;
    private String name;
}
```

## 5. Spring Data JPA 어노테이션

### @Query

커스텀 쿼리를 정의한다.

```java
public interface UserRepository extends JpaRepository<User, Long> {

    // JPQL
    @Query("SELECT u FROM User u WHERE u.email = :email")
    Optional<User> findByEmailCustom(@Param("email") String email);

    // 네이티브 쿼리
    @Query(value = "SELECT * FROM users WHERE email = :email", nativeQuery = true)
    Optional<User> findByEmailNative(@Param("email") String email);

    // DTO 프로젝션
    @Query("SELECT new com.example.dto.UserDto(u.id, u.name) FROM User u")
    List<UserDto> findAllDto();
}
```

### @Modifying

UPDATE/DELETE 쿼리를 표시한다.

```java
public interface UserRepository extends JpaRepository<User, Long> {

    @Modifying
    @Query("UPDATE User u SET u.status = :status WHERE u.id = :id")
    int updateStatus(@Param("id") Long id, @Param("status") String status);

    @Modifying
    @Query("DELETE FROM User u WHERE u.status = 'DELETED'")
    int deleteInactive();

    // clearAutomatically: 영속성 컨텍스트 초기화
    @Modifying(clearAutomatically = true)
    @Query("UPDATE User u SET u.name = :name WHERE u.id = :id")
    int updateName(@Param("id") Long id, @Param("name") String name);
}
```

### @Param

쿼리 파라미터 이름을 지정한다.

```java
@Query("SELECT u FROM User u WHERE u.name = :name AND u.age > :age")
List<User> findByNameAndAge(@Param("name") String name, @Param("age") int age);
```

### @EntityGraph

페치 조인을 선언적으로 정의한다. N+1 문제 해결.

```java
public interface OrderRepository extends JpaRepository<Order, Long> {

    // attributePaths로 즉시 로딩
    @EntityGraph(attributePaths = {"member", "orderItems"})
    List<Order> findAll();

    // 엔티티에 정의된 NamedEntityGraph 사용
    @EntityGraph(value = "Order.withMember")
    List<Order> findByStatus(String status);
}

@Entity
@NamedEntityGraph(
    name = "Order.withMember",
    attributeNodes = @NamedAttributeNode("member")
)
public class Order { }
```

## 6. 트랜잭션

### @Transactional

트랜잭션을 적용한다.

```java
@Service
@Transactional(readOnly = true)  // 클래스 레벨: 읽기 전용 기본
public class UserService {

    @Transactional  // 쓰기 작업은 readOnly = false
    public User create(UserDto dto) {
        return userRepository.save(new User(dto));
    }

    public User findById(Long id) {  // 상속받은 readOnly = true
        return userRepository.findById(id).orElseThrow();
    }

    @Transactional(
        propagation = Propagation.REQUIRED,     // 전파 옵션
        isolation = Isolation.READ_COMMITTED,   // 격리 수준
        timeout = 30,                           // 타임아웃 (초)
        rollbackFor = Exception.class           // 롤백 대상 예외
    )
    public void complexOperation() { }
}
```

**Propagation 옵션:**
| 값 | 설명 |
|----|------|
| `REQUIRED` | 기존 트랜잭션 참여, 없으면 생성 (기본값) |
| `REQUIRES_NEW` | 항상 새 트랜잭션 생성 |
| `NESTED` | 중첩 트랜잭션 |
| `SUPPORTS` | 있으면 참여, 없으면 없이 실행 |
| `NOT_SUPPORTED` | 트랜잭션 없이 실행 |

**주의사항:**
- `@Transactional`은 **public 메서드**에만 적용
- 같은 클래스 내 메서드 호출 시 트랜잭션 적용 안 됨 (프록시 우회)
- `readOnly = true`: 성능 최적화, 스냅샷 생성 안 함

## 7. Auditing

### @EnableJpaAuditing + @EntityListeners

생성/수정 시간을 자동 기록한다.

```java
@Configuration
@EnableJpaAuditing
public class JpaConfig { }

@Entity
@EntityListeners(AuditingEntityListener.class)
public class User {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @CreatedDate
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;

    @CreatedBy
    @Column(updatable = false)
    private String createdBy;

    @LastModifiedBy
    private String modifiedBy;
}
```

```java
// 작성자 정보 제공
@Component
public class AuditorAwareImpl implements AuditorAware<String> {
    @Override
    public Optional<String> getCurrentAuditor() {
        return Optional.ofNullable(SecurityContextHolder.getContext())
            .map(ctx -> ctx.getAuthentication())
            .map(auth -> auth.getName());
    }
}
```

## 8. 실전 예제

```java
@Entity
@Table(name = "orders")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = false)
    private Member member;

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderItem> orderItems = new ArrayList<>();

    @Enumerated(EnumType.STRING)
    private OrderStatus status;

    @Embedded
    private Address deliveryAddress;

    @CreatedDate
    private LocalDateTime orderedAt;

    // 생성 메서드
    public static Order create(Member member, List<OrderItem> items) {
        Order order = new Order();
        order.member = member;
        order.status = OrderStatus.ORDERED;
        items.forEach(order::addOrderItem);
        return order;
    }

    public void addOrderItem(OrderItem item) {
        orderItems.add(item);
        item.setOrder(this);
    }
}

public interface OrderRepository extends JpaRepository<Order, Long> {

    @EntityGraph(attributePaths = {"member", "orderItems"})
    List<Order> findByMemberId(Long memberId);

    @Query("SELECT o FROM Order o JOIN FETCH o.member WHERE o.status = :status")
    List<Order> findByStatusWithMember(@Param("status") OrderStatus status);

    @Modifying
    @Query("UPDATE Order o SET o.status = :status WHERE o.id = :id")
    int updateStatus(@Param("id") Long id, @Param("status") OrderStatus status);
}
```

## 정리

| 어노테이션 | 용도 |
|-----------|------|
| `@Entity` | JPA 엔티티 선언 |
| `@Table` | 테이블 매핑 설정 |
| `@Id` | 기본키 지정 |
| `@GeneratedValue` | 키 생성 전략 |
| `@Column` | 컬럼 매핑 설정 |
| `@OneToMany` / `@ManyToOne` | 1:N / N:1 관계 |
| `@JoinColumn` | 외래키 컬럼 |
| `@Embedded` | 임베디드 타입 |
| `@Query` | 커스텀 쿼리 |
| `@Modifying` | UPDATE/DELETE 쿼리 |
| `@Transactional` | 트랜잭션 적용 |
| `@EntityGraph` | 페치 조인 |
