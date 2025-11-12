# Django ForeignKey 캐싱 메커니즘 완전 분석

## 핵심 질문

**Q: ForeignKey로 연결된 객체를 수정하면, 다른 곳에서도 수정된 값이 보일까?**

**A: 네, 그렇습니다!** Django는 ForeignKey 객체를 캐시하며, **객체 참조(reference)**를 저장하기 때문입니다.

---

## Django 소스 코드 분석

### 1. ForwardManyToOneDescriptor: ForeignKey의 핵심

**파일**: `django/db/models/fields/related_descriptors.py`

```python
class ForwardManyToOneDescriptor:
    """
    Accessor to the related object on the forward side of a many-to-one or
    one-to-one (via ForwardOneToOneDescriptor subclass) relation.

    In the example::

        class Child(Model):
            parent = ForeignKey(Parent, related_name='children')

    ``Child.parent`` is a ``ForwardManyToOneDescriptor`` instance.
    """

    def __get__(self, instance, cls=None):
        """
        Get the related instance through the forward relation.

        With the example above, when getting ``child.parent``:

        - ``self`` is the descriptor managing the ``parent`` attribute
        - ``instance`` is the ``child`` instance
        - ``cls`` is the ``Child`` class (we don't need it)
        """
        if instance is None:
            return self

        # The related instance is loaded from the database and then cached
        # by the field on the model instance state. It can also be pre-cached
        # by the reverse accessor (ReverseOneToOneDescriptor).
        try:
            rel_obj = self.field.get_cached_value(instance)  # 캐시에서 가져오기
        except KeyError:
            has_value = None not in self.field.get_local_related_value(instance)
            ancestor_link = (
                instance._meta.get_ancestor_link(self.field.model)
                if has_value
                else None
            )
            if ancestor_link and ancestor_link.is_cached(instance):
                ancestor = ancestor_link.get_cached_value(instance)
                rel_obj = self.field.get_cached_value(ancestor, default=None)
            else:
                rel_obj = None
            if rel_obj is None and has_value:
                rel_obj = self.get_object(instance)  # DB에서 조회
                remote_field = self.field.remote_field
                if not remote_field.multiple:
                    remote_field.set_cached_value(rel_obj, instance)
            self.field.set_cached_value(instance, rel_obj)  # 캐시에 저장

        if rel_obj is None and not self.field.null:
            raise self.RelatedObjectDoesNotExist(
                "%s has no %s." % (self.field.model.__name__, self.field.name)
            )
        else:
            return rel_obj  # 캐시된 객체 반환
```

**핵심 포인트**:
- **Line 218**: `get_cached_value(instance)` - 캐시에서 가져오기 시도
- **Line 236**: `self.get_object(instance)` - 캐시 미스 시 DB 조회
- **Line 243**: `set_cached_value(instance, rel_obj)` - 객체를 캐시에 저장
- **Line 250**: `return rel_obj` - **동일한 캐시된 객체** 반환

---

### 2. FieldCacheMixin: 캐싱 저장소

**파일**: `django/db/models/fields/mixins.py`

```python
class FieldCacheMixin:
    """Provide an API for working with the model's fields value cache."""

    def get_cached_value(self, instance, default=NOT_PROVIDED):
        cache_name = self.get_cache_name()
        try:
            return instance._state.fields_cache[cache_name]  # 여기서 가져옴!
        except KeyError:
            if default is NOT_PROVIDED:
                raise
            return default

    def is_cached(self, instance):
        return self.get_cache_name() in instance._state.fields_cache

    def set_cached_value(self, instance, value):
        instance._state.fields_cache[self.get_cache_name()] = value  # 객체 참조 저장!

    def delete_cached_value(self, instance):
        del instance._state.fields_cache[self.get_cache_name()]
```

**핵심 포인트**:
- **Line 15**: `instance._state.fields_cache[cache_name]` - 캐시 저장소는 인스턴스의 `_state.fields_cache` 딕셔너리
- **Line 25**: `= value` - **객체의 참조(reference)**를 저장 (복사본이 아님!)

---

## 핵심 원리: 객체 참조 vs 복사본

```python
# Django는 이렇게 저장합니다:
instance._state.fields_cache['author'] = author_object  # 참조 저장

# 이렇게 하지 않습니다:
instance._state.fields_cache['author'] = copy.deepcopy(author_object)  # 복사본 저장 ❌
```

**결과**:
- 같은 메모리 주소의 객체를 공유
- 한 곳에서 수정하면 모든 곳에서 보임
- Python의 기본 객체 참조 방식

---

## 실제 예제: 블로그 시스템

### 모델 정의

```python
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()

class Post(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
```

### 시나리오 1: select_related() 사용

```python
# 1. select_related로 조회
post = Post.objects.select_related('author').first()

# 2. Author 객체가 캐시됨
# post._state.fields_cache['author'] = <Author: id=1, name="John">

# 3. author 수정
post.author.name = "John Doe (Updated)"

# 4. 같은 post 객체에서 다시 접근
print(post.author.name)
# 출력: "John Doe (Updated)"  ✅ 수정된 값!

# 5. 메모리 주소 확인
author_ref1 = post.author
author_ref2 = post.author
print(id(author_ref1) == id(author_ref2))
# 출력: True  ✅ 동일한 객체!
```

### 시나리오 2: 여러 Post가 같은 Author를 참조

```python
# 1. 같은 Author를 가진 Post들 조회
posts = Post.objects.select_related('author').filter(author_id=1)

# 2. 첫 번째 Post의 author 수정
posts[0].author.name = "Jane Doe"

# 3. 두 번째 Post의 author 확인
print(posts[1].author.name)
# 출력: "Jane Doe"  ✅ 같이 변경됨!

# 4. 왜? 같은 메모리 객체를 참조하기 때문
print(id(posts[0].author) == id(posts[1].author))
# 출력: True  ✅
```

### 시나리오 3: bulk_update 후에도 메모리 캐시는 변경된 상태 유지

```python
# 1. DB에서 조회
posts = Post.objects.select_related('author').all()
# 메모리: author.email = "john@example.com"
# DB: author.email = "john@example.com"

# 2. 메모리에서 수정
for post in posts:
    post.author.email = f"updated_{post.author.id}@example.com"
# 메모리: author.email = "updated_1@example.com"  ← 변경됨!
# DB: author.email = "john@example.com"  ← 아직 그대로

# 3. bulk_update로 DB에 저장
authors = [post.author for post in posts]
Author.objects.bulk_update(authors, ['email'])
# 메모리: author.email = "updated_1@example.com"  ← 그대로 유지!
# DB: author.email = "updated_1@example.com"  ← 업데이트됨!

# 4. 캐시는 무효화되지 않음 - 메모리의 변경된 값 그대로!
print(posts[0].author.email)
# 출력: "updated_1@example.com"  ✅ 메모리의 수정된 값!

# 5. 새로 조회하면 DB 값 가져옴
fresh_author = Author.objects.get(id=posts[0].author.id)
print(fresh_author.email)
# 출력: "updated_1@example.com"  ✅ DB에서 새로 읽음
```

**핵심 포인트**:
- `bulk_update()`는 **메모리 → DB 저장만** 함
- **캐시를 무효화하지 않음** (DB에서 다시 읽지 않음)
- 따라서 **메모리에서 수정한 값이 계속 유지됨**

---

## 동작 흐름도

```
┌─────────────────────────────────────────────────────────────┐
│ 1. select_related('author')로 조회                           │
│    → Author 객체가 메모리에 로드됨                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. post._state.fields_cache['author'] = <Author object>     │
│    → 객체 참조가 캐시에 저장됨                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. post.author 접근                                          │
│    → ForwardManyToOneDescriptor.__get__() 호출               │
│    → get_cached_value() 실행                                 │
│    → fields_cache에서 객체 반환                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. post.author.name = "변경"                                 │
│    → 캐시된 객체가 직접 수정됨                                │
│    → Python 객체 참조 방식                                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. 다시 post.author.name 접근                                │
│    → 여전히 같은 캐시된 객체 반환                             │
│    → "변경" 출력! ✅                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 주의사항

### 1. bulk_update()는 캐시를 무효화하지 않음 (메모리 수정값 유지)

```python
# 조회
post = Post.objects.select_related('author').first()
# 메모리: name="John", DB: name="John"

# 메모리에서 수정
post.author.name = "Jane"
# 메모리: name="Jane", DB: name="John"

# bulk_update 실행
Author.objects.bulk_update([post.author], ['name'])
# 메모리: name="Jane" ← 여전히 "Jane"!
# DB: name="Jane" ← 업데이트됨

# 캐시는 무효화되지 않고, 메모리의 수정값이 계속 유지됨
print(post.author.name)
# 출력: "Jane"  ✅ 메모리의 수정된 값!

# ⚠️ DB를 직접 수정한 경우는 다름
Author.objects.filter(id=post.author.id).update(name="Alice")
# 메모리: name="Jane" ← 여전히 "Jane"!
# DB: name="Alice" ← 업데이트됨
print(post.author.name)
# 출력: "Jane"  ⚠️ 메모리 캐시가 오래된 값!
```

### 2. refresh_from_db()로 캐시 새로고침

```python
# 캐시를 무효화하고 DB에서 다시 로드
post.author.refresh_from_db()

# 이제 DB의 최신 값이 로드됨
print(post.author.name)
```

### 3. 같은 객체를 여러 곳에서 참조

```python
# 여러 Post가 같은 Author를 참조하면
# 한 곳에서 수정하면 모든 곳에서 보임!
posts = Post.objects.select_related('author').filter(author_id=1)
posts[0].author.name = "Changed"
print(posts[1].author.name)  # "Changed" 출력!
```

---

## 실전 팁

### 언제 이 동작이 중요한가?

#### 1. 연쇄 필터링 작업

```python
# Step 1: 기본 필터링
posts = Post.objects.select_related('author').all()

# Step 2: author 정보 보강 (외부 API 호출 등)
for post in posts:
    post.author.email = fetch_email_from_api(post.author.id)

# Step 3: DB 저장
authors = [post.author for post in posts]
Author.objects.bulk_update(authors, ['email'])

# Step 4: 추가 필터링
verified_posts = [
    post for post in posts
    if is_verified_email(post.author.email)  # ✅ 이미 업데이트된 email 사용!
]
```

#### 2. 복잡한 비즈니스 로직

```python
# 여러 단계의 필터링과 수정
posts = Post.objects.select_related('author').all()

# 1단계: author 검증
for post in posts:
    post.author.is_verified = verify_author(post.author)

# 2단계: 검증된 author의 posts만 필터링
verified_posts = [post for post in posts if post.author.is_verified]

# 3단계: 추가 로직
for post in verified_posts:
    process(post.author)  # ✅ 여전히 수정된 author 사용 가능
```

### 성능 이점

```python
# N+1 쿼리 방지
posts = Post.objects.select_related('author').all()

for post in posts:
    # 추가 DB 쿼리 없음! 캐시된 객체 사용
    print(post.author.name)
    print(post.author.email)

# 단 1개의 쿼리만 실행됨 (JOIN 사용)
```

---

## 검증 방법

### Python id() 함수로 확인

```python
post = Post.objects.select_related('author').first()

# 같은 객체인지 확인
ref1 = post.author
ref2 = post.author

print(f"ref1 id: {id(ref1)}")
print(f"ref2 id: {id(ref2)}")
print(f"Same object? {id(ref1) == id(ref2)}")  # True

# 수정 후에도 같은 객체
ref1.name = "Modified"
print(f"ref2.name: {ref2.name}")  # "Modified" 출력!
```

### Django Shell에서 직접 확인

```python
# Django shell에서 실행
python manage.py shell

>>> from myapp.models import Post
>>> post = Post.objects.select_related('author').first()
>>>
>>> # 캐시 확인
>>> 'author' in post._state.fields_cache
True
>>>
>>> # 캐시된 객체 확인
>>> cached_author = post._state.fields_cache['author']
>>> post.author is cached_author
True
>>>
>>> # 수정 테스트
>>> post.author.name = "Test"
>>> cached_author.name
'Test'  # ✅ 같은 객체!
```

---

## 결론

Django의 ForeignKey는 **객체 참조(reference)를 캐시**하기 때문에:

✅ **한 곳에서 수정하면 모든 곳에서 보임**
✅ **bulk_update() 후에도 메모리 객체는 유지됨**
✅ **추가 DB 쿼리 없이 수정된 값 사용 가능**
✅ **select_related()로 N+1 쿼리 방지**

이 메커니즘을 이해하면:
- 불필요한 `refresh_from_db()` 호출 방지
- 효율적인 데이터 처리 파이프라인 구축
- 복잡한 필터링 로직 체이닝 가능

---

## 참고 문서

- Django 소스 코드:
    - `django/db/models/fields/related_descriptors.py` (Line 115-250)
    - `django/db/models/fields/mixins.py` (Line 6-28)
- Django 공식 문서: [select_related()](https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-related)
- Python 객체 참조: [Data Model](https://docs.python.org/3/reference/datamodel.html)
