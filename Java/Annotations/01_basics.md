# Java 기본 어노테이션

## 어노테이션이란?

어노테이션(Annotation)은 코드에 메타데이터를 추가하는 방법이다. `@` 기호로 시작하며, 컴파일러에게 정보를 제공하거나 런타임에 특정 동작을 수행하도록 한다.

```java
@Override
public String toString() {
    return "Hello";
}
```

## 1. 표준 어노테이션

### @Override

부모 클래스나 인터페이스의 메서드를 오버라이드함을 명시한다. 컴파일러가 실제로 오버라이드가 맞는지 검증해준다.

```java
class Parent {
    void sayHello() { }
}

class Child extends Parent {
    @Override
    void sayHello() {  // OK: 올바른 오버라이드
        System.out.println("Hello from Child");
    }

    @Override
    void sayHelo() {  // 컴파일 에러! 오타로 인해 오버라이드가 아님
    }
}
```

**왜 사용하나?**
- 오타로 인한 실수 방지
- 부모 메서드 시그니처 변경 시 컴파일 에러로 알려줌

### @Deprecated

더 이상 사용을 권장하지 않는 요소임을 표시한다. 사용하면 컴파일 경고가 발생한다.

```java
public class LegacyApi {

    @Deprecated
    public void oldMethod() {
        // 구버전 호환용으로 유지
    }

    @Deprecated(since = "1.5", forRemoval = true)
    public void veryOldMethod() {
        // since: 언제부터 deprecated인지
        // forRemoval: 향후 삭제 예정 여부
    }

    public void newMethod() {
        // 이 메서드를 사용하세요
    }
}
```

### @SuppressWarnings

특정 컴파일러 경고를 무시한다.

```java
// 단일 경고 억제
@SuppressWarnings("unchecked")
List<String> list = (List<String>) rawList;

// 복수 경고 억제
@SuppressWarnings({"unchecked", "deprecation"})
public void legacyMethod() {
    // ...
}
```

**주요 경고 타입:**
| 값 | 설명 |
|----|------|
| `unchecked` | 제네릭 타입 미검사 경고 |
| `deprecation` | deprecated 요소 사용 경고 |
| `rawtypes` | raw 타입 사용 경고 |
| `unused` | 사용하지 않는 코드 경고 |
| `serial` | serialVersionUID 누락 경고 |
| `all` | 모든 경고 |

### @FunctionalInterface

함수형 인터페이스(추상 메서드가 딱 하나인 인터페이스)임을 명시한다.

```java
@FunctionalInterface
public interface Calculator {
    int calculate(int a, int b);  // 추상 메서드는 하나만!

    // default, static 메서드는 가능
    default void print() { }
    static void helper() { }
}

// 람다로 사용 가능
Calculator add = (a, b) -> a + b;
Calculator multiply = (a, b) -> a * b;
```

```java
@FunctionalInterface
public interface WrongInterface {
    void method1();
    void method2();  // 컴파일 에러! 추상 메서드가 2개
}
```

### @SafeVarargs

제네릭 가변인자 사용 시 타입 안전성을 보장함을 선언한다.

```java
public class VarargsExample {

    // 경고 발생: Possible heap pollution
    public static <T> void unsafeMethod(T... elements) {
        // ...
    }

    // 경고 억제: 개발자가 안전함을 보장
    @SafeVarargs
    public static <T> void safeMethod(T... elements) {
        for (T element : elements) {
            System.out.println(element);
        }
    }
}
```

**제약사항:**
- `final`, `static`, `private` 메서드 또는 생성자에만 사용 가능
- 실제로 안전한 경우에만 사용해야 함

## 2. 메타 어노테이션

메타 어노테이션은 **어노테이션을 정의할 때 사용하는 어노테이션**이다. 커스텀 어노테이션을 만들 때 필수적으로 알아야 한다.

### @Target

어노테이션을 어디에 적용할 수 있는지 지정한다.

```java
@Target(ElementType.METHOD)  // 메서드에만 적용 가능
public @interface MethodOnly { }

@Target({ElementType.TYPE, ElementType.METHOD})  // 클래스와 메서드에 적용 가능
public @interface TypeAndMethod { }
```

**ElementType 종류:**
| 값 | 적용 대상 |
|----|----------|
| `TYPE` | 클래스, 인터페이스, enum |
| `FIELD` | 필드 (멤버 변수) |
| `METHOD` | 메서드 |
| `PARAMETER` | 메서드 파라미터 |
| `CONSTRUCTOR` | 생성자 |
| `LOCAL_VARIABLE` | 지역 변수 |
| `ANNOTATION_TYPE` | 다른 어노테이션 |
| `PACKAGE` | 패키지 |
| `TYPE_PARAMETER` | 타입 파라미터 (제네릭) |
| `TYPE_USE` | 타입 사용 위치 (Java 8+) |

### @Retention

어노테이션 정보를 언제까지 유지할지 지정한다.

```java
@Retention(RetentionPolicy.RUNTIME)
public @interface RuntimeAnnotation { }

@Retention(RetentionPolicy.SOURCE)
public @interface SourceOnlyAnnotation { }
```

**RetentionPolicy 종류:**
| 값 | 설명 | 용도 |
|----|------|------|
| `SOURCE` | 소스 파일에만 존재, 컴파일 시 제거 | `@Override`, `@SuppressWarnings` |
| `CLASS` | 클래스 파일까지 유지, 런타임에는 사용 불가 (기본값) | 바이트코드 분석용 |
| `RUNTIME` | 런타임에도 유지, 리플렉션으로 접근 가능 | Spring, JPA 등 대부분의 프레임워크 |

**중요:** 대부분의 실용적인 어노테이션은 `RUNTIME`을 사용한다. 리플렉션으로 읽어서 처리해야 하기 때문.

### @Documented

Javadoc에 어노테이션 정보를 포함시킨다.

```java
@Documented
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface ImportantMethod { }
```

### @Inherited

클래스에 적용된 어노테이션이 자식 클래스에도 상속된다. **클래스에만 적용**되며 인터페이스에는 적용되지 않는다.

```java
@Inherited
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
public @interface InheritedAnnotation { }

@InheritedAnnotation
class Parent { }

class Child extends Parent { }  // Child도 @InheritedAnnotation을 가짐!
```

```java
// 확인
Child.class.isAnnotationPresent(InheritedAnnotation.class);  // true
```

### @Repeatable

같은 어노테이션을 여러 번 적용할 수 있게 한다. 컨테이너 어노테이션이 필요하다.

```java
// 1. 반복 가능 어노테이션
@Repeatable(Schedules.class)
@Retention(RetentionPolicy.RUNTIME)
public @interface Schedule {
    String dayOfWeek();
    String time();
}

// 2. 컨테이너 어노테이션
@Retention(RetentionPolicy.RUNTIME)
public @interface Schedules {
    Schedule[] value();
}

// 3. 사용
@Schedule(dayOfWeek = "Mon", time = "09:00")
@Schedule(dayOfWeek = "Wed", time = "14:00")
@Schedule(dayOfWeek = "Fri", time = "16:00")
public class Meeting { }
```

## 3. 어노테이션 구조

어노테이션은 특수한 형태의 인터페이스다.

```java
public @interface MyAnnotation {
    // 요소(element) 정의 - 메서드처럼 보이지만 속성 역할
    String name();                    // 필수 요소
    int count() default 1;           // 기본값 있는 요소
    String[] tags() default {};      // 배열 요소
    Class<?> type() default Object.class;  // Class 요소
}

// 사용
@MyAnnotation(name = "test", count = 5, tags = {"a", "b"})
public class Sample { }
```

**요소 타입으로 사용 가능한 것:**
- 기본 타입 (int, boolean 등)
- String
- Class
- Enum
- 다른 어노테이션
- 위 타입들의 배열

**value 요소:**
요소가 하나뿐이고 이름이 `value`면 이름 생략 가능.

```java
public @interface SingleValue {
    String value();
}

@SingleValue("hello")  // @SingleValue(value = "hello")와 동일
public class Sample { }
```

## 4. 리플렉션으로 어노테이션 읽기

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface Test {
    String name() default "";
}

public class MyTest {
    @Test(name = "addition test")
    public void testAdd() { }

    @Test
    public void testSubtract() { }

    public void normalMethod() { }
}
```

```java
// 어노테이션 읽기
Class<?> clazz = MyTest.class;

for (Method method : clazz.getDeclaredMethods()) {
    if (method.isAnnotationPresent(Test.class)) {
        Test test = method.getAnnotation(Test.class);
        System.out.println("Test method: " + method.getName());
        System.out.println("Test name: " + test.name());
    }
}
```

**출력:**
```
Test method: testAdd
Test name: addition test
Test method: testSubtract
Test name:
```

## 정리

| 어노테이션 | 용도 |
|-----------|------|
| `@Override` | 오버라이드 검증 |
| `@Deprecated` | 사용 자제 권고 |
| `@SuppressWarnings` | 경고 억제 |
| `@FunctionalInterface` | 함수형 인터페이스 검증 |
| `@SafeVarargs` | 제네릭 가변인자 안전 선언 |
| `@Target` | 어노테이션 적용 위치 |
| `@Retention` | 어노테이션 유지 정책 |
| `@Documented` | Javadoc 포함 |
| `@Inherited` | 상속 전파 |
| `@Repeatable` | 반복 적용 허용 |
