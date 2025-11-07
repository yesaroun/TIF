# Django 데이터베이스 인덱스 (Database Indexes)

## 목차
1. [인덱스 기본 개념](#인덱스-기본-개념)
2. [Django에서 인덱스 사용하기](#django에서-인덱스-사용하기)
3. [기본 인덱스](#기본-인덱스)
4. [복합 인덱스 (Composite Index)](#복합-인덱스-composite-index)
5. [부분 인덱스 (Partial Index)](#부분-인덱스-partial-index)
6. [함수 기반 인덱스 (Functional Index)](#함수-기반-인덱스-functional-index)
7. [인덱스 종류별 상세 설명](#인덱스-종류별-상세-설명)
8. [성능 최적화 전략](#성능-최적화-전략)
9. [실전 예제](#실전-예제)
10. [주의사항 및 베스트 프랙티스](#주의사항-및-베스트-프랙티스)

---

## 인덱스 기본 개념

### 인덱스란?

인덱스는 데이터베이스 테이블의 **검색 속도를 향상**시키기 위한 자료구조입니다. 책의 색인(index)과 유사한 개념으로, 특정 데이터를 빠르게 찾을 수 있도록 도와줍니다.

### 인덱스의 작동 원리

```
인덱스 없이 검색 (Full Table Scan):
┌─────┬──────┬─────┬────────┐
│ ID  │ Name │ Age │ Email  │
├─────┼──────┼─────┼────────┤
│ 1   │ Alice│ 25  │ a@...  │ ← 첫 행부터
│ 2   │ Bob  │ 30  │ b@...  │ ← 순차적으로
│ 3   │ Carol│ 28  │ c@...  │ ← 모든 행을
│ ... │ ...  │ ... │ ...    │ ← 검색
│ 1000│ Zoe  │ 35  │ z@...  │ ← 마지막까지
└─────┴──────┴─────┴────────┘

인덱스로 검색 (Index Scan):
Name 인덱스 (B-Tree 구조)
        "M"
       /   \
    "D"     "T"
   /  \     /  \
 "A" "H" "P" "Z"
  ↓
특정 값으로 바로 점프!
```

### 인덱스의 장단점

**장점:**
- 🚀 **검색 속도 향상**: WHERE, JOIN, ORDER BY 쿼리가 빨라짐
- 📊 **정렬 최적화**: ORDER BY 절의 성능 개선
- 🎯 **유니크 제약**: 데이터 무결성 보장

**단점:**
- 💾 **저장 공간 증가**: 추가 디스크 공간 필요
- ⏱️ **쓰기 성능 저하**: INSERT, UPDATE, DELETE 시 인덱스도 갱신 필요
- 🔧 **유지보수 비용**: 인덱스 관리 필요

---

## Django에서 인덱스 사용하기

### 인덱스 정의 방법

Django에서는 세 가지 주요 방법으로 인덱스를 정의할 수 있습니다:

#### 1. 필드 레벨 인덱스 (Field-level)

```python
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)  # 단일 필드 인덱스
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### 2. Meta 클래스 인덱스 (Meta.indexes)

```python
class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),                    # 단일 인덱스
            models.Index(fields=['category', 'price']),       # 복합 인덱스
            models.Index(fields=['-created_at']),             # 내림차순 인덱스
        ]
```

#### 3. 제약조건을 통한 인덱스 (Constraints)

```python
from django.db.models import Q, UniqueConstraint

class Product(models.Model):
    sku = models.CharField(max_length=50)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            # 삭제되지 않은 항목만 SKU 유니크 보장
            UniqueConstraint(
                fields=['sku'],
                condition=Q(is_deleted=False),
                name='unique_active_sku'
            )
        ]
```

---

## 기본 인덱스

### 단일 컬럼 인덱스

가장 기본적인 형태의 인덱스로, 하나의 컬럼에 대해 생성됩니다.

```python
class User(models.Model):
    email = models.EmailField(unique=True)           # 자동으로 유니크 인덱스 생성
    username = models.CharField(max_length=50, db_index=True)  # 일반 인덱스
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_at'], name='user_created_idx'),
        ]
```

**생성되는 SQL:**
```sql
CREATE INDEX user_username_idx ON app_user (username);
CREATE INDEX user_created_idx ON app_user (created_at);
CREATE UNIQUE INDEX user_email_unique ON app_user (email);
```

**효과적인 쿼리:**
```python
# ✅ 인덱스 활용 (빠름)
User.objects.filter(username='john')
User.objects.filter(email='john@example.com')
User.objects.order_by('created_at')

# ❌ 인덱스 미활용 (느림)
User.objects.filter(first_name='John')  # first_name에 인덱스 없음
```

### 자동 생성되는 인덱스

Django가 자동으로 인덱스를 생성하는 경우:

```python
class Article(models.Model):
    # 1. Primary Key (자동 인덱스)
    id = models.AutoField(primary_key=True)

    # 2. Unique 필드 (자동 유니크 인덱스)
    slug = models.SlugField(unique=True)

    # 3. Foreign Key (자동 인덱스)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    # 4. OneToOne (자동 유니크 인덱스)
    detail = models.OneToOneField('ArticleDetail', on_delete=models.CASCADE)
```

---

## 복합 인덱스 (Composite Index)

### 개념

여러 컬럼을 조합한 인덱스로, 다중 조건 검색 시 유용합니다.

### 기본 사용법

```python
class Order(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        indexes = [
            # 복합 인덱스: customer + status
            models.Index(fields=['customer', 'status'], name='order_cust_status_idx'),

            # 복합 인덱스: status + created_at (내림차순)
            models.Index(fields=['status', '-created_at'], name='order_status_date_idx'),

            # 3개 컬럼 복합 인덱스
            models.Index(
                fields=['customer', 'status', 'created_at'],
                name='order_cust_status_date_idx'
            ),
        ]
```

### 복합 인덱스의 컬럼 순서 (매우 중요!)

**왼쪽 접두사 규칙 (Leftmost Prefix Rule):**

```python
# 인덱스: ['customer', 'status', 'created_at']

# ✅ 인덱스 활용 가능
Order.objects.filter(customer=user)                                    # customer만
Order.objects.filter(customer=user, status='pending')                  # customer + status
Order.objects.filter(customer=user, status='pending', created_at=date) # 모두 사용

# ❌ 인덱스 활용 불가 또는 비효율적
Order.objects.filter(status='pending')                                 # customer 없음
Order.objects.filter(created_at=date)                                  # customer 없음
Order.objects.filter(status='pending', created_at=date)                # customer 없음
```

### 컬럼 순서 결정 기준

```python
class Product(models.Model):
    category = models.CharField(max_length=50)     # 카디널리티 낮음 (10개 카테고리)
    brand = models.CharField(max_length=50)        # 카디널리티 중간 (100개 브랜드)
    sku = models.CharField(max_length=100)         # 카디널리티 높음 (10000개 SKU)
    is_active = models.BooleanField()              # 카디널리티 매우 낮음 (2개 값)

    class Meta:
        indexes = [
            # ❌ 비효율적 순서
            models.Index(fields=['is_active', 'category', 'brand']),

            # ✅ 효율적 순서
            # 1. 자주 사용되는 조건이 앞에
            # 2. 카디널리티 높은 순서 (선택적)
            models.Index(fields=['category', 'brand', 'is_active']),
        ]
```

**실전 예제:**
```python
class BlogPost(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)  # draft, published, archived
    published_at = models.DateTimeField(null=True)
    view_count = models.IntegerField(default=0)

    class Meta:
        indexes = [
            # 블로그 목록: 작성자별 발행된 글을 최신순으로
            models.Index(
                fields=['author', 'status', '-published_at'],
                name='post_author_status_date_idx'
            ),

            # 인기 게시물: 상태별로 조회수 높은 순
            models.Index(
                fields=['status', '-view_count'],
                name='post_status_views_idx'
            ),
        ]

# 효율적인 쿼리
BlogPost.objects.filter(
    author=user,
    status='published'
).order_by('-published_at')  # post_author_status_date_idx 사용
```

---

## 부분 인덱스 (Partial Index)

### 개념

조건을 만족하는 행에만 인덱스를 생성하여 **인덱스 크기를 줄이고 성능을 향상**시킵니다.

### 기본 사용법

```python
from django.db.models import Q, Index

class Order(models.Model):
    status = models.CharField(max_length=20)
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)

    class Meta:
        indexes = [
            # 미결제 주문만 인덱스 생성
            Index(
                fields=['customer', 'created_at'],
                condition=Q(is_paid=False),
                name='unpaid_orders_idx'
            ),

            # 활성 상태 주문만 인덱스
            Index(
                fields=['status', '-created_at'],
                condition=Q(status__in=['pending', 'processing']),
                name='active_orders_idx'
            ),
        ]
```

### 실전 활용 예제

#### 1. 소프트 삭제 (Soft Delete) 패턴

```python
class Article(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField()
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        indexes = [
            # 삭제되지 않은 게시글만 인덱스 (대부분의 쿼리가 이것을 사용)
            Index(
                fields=['slug'],
                condition=Q(is_deleted=False),
                name='active_article_slug_idx'
            ),
        ]

        constraints = [
            # 활성 게시글만 slug 유니크 제약
            UniqueConstraint(
                fields=['slug'],
                condition=Q(is_deleted=False),
                name='unique_active_slug'
            )
        ]

# 효율적인 쿼리
Article.objects.filter(is_deleted=False, slug='django-indexes')  # 인덱스 활용
```

#### 2. 날짜 범위 최적화

```python
from django.utils import timezone
from datetime import timedelta

class Event(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            # 향후 30일 이내 이벤트만 인덱스 (자주 조회되는 데이터)
            Index(
                fields=['start_date', 'end_date'],
                condition=Q(
                    start_date__gte=timezone.now(),
                    is_active=True
                ),
                name='upcoming_events_idx'
            ),
        ]
```

#### 3. NULL 값 제외

```python
class Product(models.Model):
    name = models.CharField(max_length=200)
    discontinued_at = models.DateTimeField(null=True, blank=True)
    special_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    class Meta:
        indexes = [
            # 단종되지 않은 제품만 인덱스
            Index(
                fields=['name'],
                condition=Q(discontinued_at__isnull=True),
                name='active_product_idx'
            ),

            # 특별 가격이 있는 제품만 인덱스
            Index(
                fields=['special_price'],
                condition=Q(special_price__isnull=False),
                name='special_price_idx'
            ),
        ]
```

### 부분 인덱스의 장점

```python
# 전체 인덱스 vs 부분 인덱스 비교

class Task(models.Model):
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20)  # pending, completed, cancelled
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            # ❌ 전체 인덱스: 모든 상태 포함 (비효율적)
            # Index(fields=['status', 'assigned_to']),

            # ✅ 부분 인덱스: pending 상태만 (효율적)
            # - 인덱스 크기 60-70% 감소 (pending이 전체의 30%라면)
            # - 검색 속도 향상
            # - 디스크 I/O 감소
            Index(
                fields=['assigned_to', 'status'],
                condition=Q(status='pending'),
                name='pending_tasks_idx'
            ),
        ]

# 대부분의 쿼리가 미완료 작업을 조회
Task.objects.filter(status='pending', assigned_to=user)
```

---

## 함수 기반 인덱스 (Functional Index)

### 개념

함수나 표현식을 적용한 결과에 대해 인덱스를 생성합니다. Django 5.0+에서 지원합니다.

### 기본 사용법

```python
from django.db.models import F, Q, Index
from django.db.models.functions import Lower, Upper, ExtractYear

class User(models.Model):
    email = models.EmailField()
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # 대소문자 구분 없는 이메일 검색
            Index(Lower('email'), name='user_email_lower_idx'),

            # 전체 이름 검색 (first_name + last_name)
            Index(F('first_name'), F('last_name'), name='user_fullname_idx'),
        ]
```

### 실전 활용 사례

#### 1. 대소문자 무시 검색

```python
class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50)

    class Meta:
        indexes = [
            # 대소문자 무시 검색 최적화
            Index(Lower('name'), name='product_name_lower_idx'),
            Index(Upper('sku'), name='product_sku_upper_idx'),
        ]

# 효율적인 쿼리
from django.db.models.functions import Lower

# ✅ 인덱스 활용
Product.objects.filter(name__lower='iphone 15')
Product.objects.annotate(
    name_lower=Lower('name')
).filter(name_lower='iphone 15')

# ❌ 인덱스 미활용
Product.objects.filter(name__iexact='iphone 15')  # 일반 인덱스는 사용 불가
```

#### 2. 날짜/시간 추출

```python
from django.db.models.functions import ExtractYear, ExtractMonth

class Sale(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    sold_at = models.DateTimeField()

    class Meta:
        indexes = [
            # 연도별 집계 최적화
            Index(ExtractYear('sold_at'), name='sale_year_idx'),

            # 연도+월별 집계 최적화
            Index(
                ExtractYear('sold_at'),
                ExtractMonth('sold_at'),
                name='sale_year_month_idx'
            ),
        ]

# 연도별 매출 조회
from django.db.models.functions import ExtractYear

Sale.objects.annotate(
    year=ExtractYear('sold_at')
).filter(year=2024).aggregate(Sum('amount'))
```

#### 3. 계산 필드 인덱스

```python
from django.db.models import F

class OrderItem(models.Model):
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        indexes = [
            # 총액 계산 결과에 인덱스
            Index(
                F('quantity') * F('unit_price') * (1 - F('discount')),
                name='orderitem_total_idx'
            ),
        ]

# 특정 금액 이상 주문 항목 검색
OrderItem.objects.annotate(
    total=F('quantity') * F('unit_price') * (1 - F('discount'))
).filter(total__gte=1000)
```

#### 4. JSON 필드 인덱스 (PostgreSQL)

```python
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import GinIndex

class Product(models.Model):
    name = models.CharField(max_length=200)
    attributes = models.JSONField()  # {"color": "red", "size": "L"}

    class Meta:
        indexes = [
            # JSON 필드 전체 GIN 인덱스
            GinIndex(fields=['attributes'], name='product_attrs_gin_idx'),
        ]

# JSON 검색
Product.objects.filter(attributes__color='red')
Product.objects.filter(attributes__size='L')
```

---

## 인덱스 종류별 상세 설명

### 1. B-Tree 인덱스 (기본)

가장 일반적인 인덱스 타입으로, 대부분의 경우 사용됩니다.

```python
class Article(models.Model):
    title = models.CharField(max_length=200)
    view_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['title']),           # B-Tree (기본)
            models.Index(fields=['view_count']),      # B-Tree (범위 검색에 적합)
            models.Index(fields=['-created_at']),     # B-Tree (정렬 지원)
        ]

# B-Tree가 효율적인 쿼리
Article.objects.filter(view_count__gte=1000)          # 범위 검색
Article.objects.filter(title__startswith='Django')    # 접두사 검색
Article.objects.order_by('-created_at')               # 정렬
```

### 2. Hash 인덱스 (PostgreSQL)

정확한 일치 검색에만 사용 가능합니다.

```python
from django.contrib.postgres.indexes import HashIndex

class Session(models.Model):
    session_key = models.CharField(max_length=40, unique=True)
    session_data = models.TextField()

    class Meta:
        indexes = [
            # Hash 인덱스: = 연산만 지원, B-Tree보다 빠르고 작음
            HashIndex(fields=['session_key'], name='session_key_hash_idx'),
        ]

# ✅ 효율적
Session.objects.get(session_key='abc123...')

# ❌ 사용 불가
Session.objects.filter(session_key__startswith='abc')  # LIKE는 Hash 인덱스 사용 불가
```

### 3. GIN/GiST 인덱스 (PostgreSQL - 전문 검색)

```python
from django.contrib.postgres.indexes import GinIndex, GistIndex
from django.contrib.postgres.search import SearchVectorField

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    search_vector = SearchVectorField(null=True)
    tags = models.JSONField(default=list)

    class Meta:
        indexes = [
            # GIN: 전문 검색 (Full-Text Search)
            GinIndex(fields=['search_vector'], name='article_search_gin_idx'),

            # GIN: 배열/JSON 검색
            GinIndex(fields=['tags'], name='article_tags_gin_idx'),
        ]

# 전문 검색
from django.contrib.postgres.search import SearchQuery, SearchRank

Article.objects.annotate(
    rank=SearchRank('search_vector', SearchQuery('django'))
).filter(search_vector=SearchQuery('django')).order_by('-rank')

# JSON 배열 검색
Article.objects.filter(tags__contains=['python', 'django'])
```

### 4. 커버링 인덱스 (Covering Index)

쿼리에 필요한 모든 컬럼을 인덱스에 포함시켜 테이블 접근을 줄입니다.

```python
class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()

    class Meta:
        indexes = [
            # 커버링 인덱스: 쿼리가 필요로 하는 모든 컬럼 포함
            models.Index(
                fields=['category', 'price'],
                include=['name', 'stock'],  # Django 4.2+
                name='product_category_covering_idx'
            ),
        ]

# ✅ 인덱스만으로 쿼리 완료 (테이블 접근 불필요)
Product.objects.filter(
    category='electronics',
    price__lte=1000
).values('name', 'stock')  # name, stock이 include에 포함됨
```

---

## 성능 최적화 전략

### 1. 인덱스가 필요한 경우

```python
class Order(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # ✅ 인덱스 필요: 자주 WHERE 절에 사용
            models.Index(fields=['status']),

            # ✅ 인덱스 필요: 자주 JOIN에 사용 (FK는 자동 생성)
            # models.Index(fields=['customer']),  # 이미 FK로 자동 생성됨

            # ✅ 인덱스 필요: 자주 ORDER BY에 사용
            models.Index(fields=['-created_at']),
        ]

# 빈번한 쿼리 패턴
Order.objects.filter(status='pending').order_by('-created_at')
Order.objects.filter(customer=user, status='shipped')
```

### 2. 인덱스가 불필요한 경우

```python
class Log(models.Model):
    message = models.TextField()              # ❌ 텍스트는 인덱스 비효율적
    level = models.CharField(max_length=10)   # ❌ 카디널리티 낮음 (5개 값)
    created_at = models.DateTimeField()       # ✅ 하지만 시계열 데이터라면 필요
    metadata = models.JSONField()             # ❌ 일반 인덱스 불가, GIN 고려

    class Meta:
        indexes = [
            # level은 카디널리티가 낮지만, 자주 필터링된다면 부분 인덱스 고려
            models.Index(
                fields=['level', '-created_at'],
                condition=Q(level__in=['ERROR', 'CRITICAL']),
                name='error_log_idx'
            ),
        ]
```

### 3. 쿼리 분석 및 최적화

```python
from django.db import connection

# 쿼리 실행 계획 확인
def analyze_query():
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN ANALYZE SELECT * FROM app_order WHERE status = 'pending'")
        print(cursor.fetchall())

# 인덱스 사용 확인
Order.objects.filter(status='pending').explain(verbose=True, analyze=True)
```

**출력 예시:**
```
Seq Scan on app_order  (cost=0.00..18.50 rows=5 width=100)  ← 인덱스 미사용!
  Filter: (status = 'pending')

Index Scan using order_status_idx on app_order  (cost=0.15..8.17 rows=5)  ← 인덱스 사용!
  Index Cond: (status = 'pending')
```

### 4. 인덱스 모니터링

```python
# PostgreSQL: 인덱스 사용 통계
from django.db import connection

def check_index_usage():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan,           -- 인덱스 스캔 횟수
                idx_tup_read,       -- 읽은 행 수
                idx_tup_fetch       -- 반환된 행 수
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
            ORDER BY idx_scan ASC;  -- 사용 빈도 낮은 순
        """)

        for row in cursor.fetchall():
            print(f"Index: {row[2]}, Scans: {row[3]}")
            if row[3] == 0:
                print(f"⚠️  Unused index: {row[2]}")
```

---

## 실전 예제

### 예제 1: E-Commerce 제품 모델

```python
from django.db import models
from django.db.models import Q, Index, UniqueConstraint
from django.contrib.postgres.indexes import GinIndex

class Product(models.Model):
    # 기본 정보
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=100)

    # 카테고리 및 분류
    category = models.ForeignKey('Category', on_delete=models.PROTECT)
    brand = models.ForeignKey('Brand', on_delete=models.PROTECT)
    tags = models.JSONField(default=list)

    # 가격 및 재고
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)

    # 상태
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.IntegerField(default=0)

    class Meta:
        indexes = [
            # 1. 제품 목록 (카테고리별, 최신순)
            Index(
                fields=['category', '-created_at'],
                condition=Q(is_active=True),
                name='active_product_list_idx'
            ),

            # 2. 브랜드별 제품 (인기순)
            Index(
                fields=['brand', '-view_count'],
                condition=Q(is_active=True, stock__gt=0),
                name='brand_popular_idx'
            ),

            # 3. 가격 필터링 (카테고리 + 가격 범위)
            Index(
                fields=['category', 'price'],
                condition=Q(is_active=True),
                name='category_price_idx'
            ),

            # 4. 추천 제품 (Featured)
            Index(
                fields=['-view_count'],
                condition=Q(is_featured=True, is_active=True),
                name='featured_products_idx'
            ),

            # 5. 태그 검색 (PostgreSQL)
            GinIndex(
                fields=['tags'],
                name='product_tags_gin_idx'
            ),

            # 6. 재고 관리 (재고 부족 제품)
            Index(
                fields=['category', 'stock'],
                condition=Q(stock__lte=10, is_active=True),
                name='low_stock_idx'
            ),
        ]

        constraints = [
            # SKU 유니크 제약 (활성 제품만)
            UniqueConstraint(
                fields=['sku'],
                condition=Q(is_active=True),
                name='unique_active_sku'
            )
        ]

# 쿼리 예시
class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def in_stock(self):
        return self.filter(stock__gt=0)

    def by_category(self, category):
        # category_price_idx 또는 active_product_list_idx 사용
        return self.active().filter(category=category)

    def price_range(self, min_price, max_price):
        # category_price_idx 사용
        return self.filter(price__gte=min_price, price__lte=max_price)

    def featured(self):
        # featured_products_idx 사용
        return self.filter(is_featured=True, is_active=True).order_by('-view_count')

class Product(models.Model):
    # ... (위의 필드들)
    objects = ProductQuerySet.as_manager()

# 사용 예
Product.objects.by_category(category).price_range(100, 500).in_stock()
Product.objects.featured()[:10]
```

### 예제 2: 소셜 미디어 게시물

```python
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField

class Post(models.Model):
    # 작성자 정보
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    # 내용
    title = models.CharField(max_length=200)
    content = models.TextField()
    search_vector = SearchVectorField(null=True)

    # 상태
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('published', 'Published'),
            ('archived', 'Archived'),
        ],
        default='draft'
    )

    # 통계
    like_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)

    # 날짜
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # 1. 피드 (팔로우하는 사람들의 게시물, 최신순)
            Index(
                fields=['author', '-published_at'],
                condition=Q(status='published'),
                name='post_feed_idx'
            ),

            # 2. 인기 게시물 (좋아요 순)
            Index(
                fields=['-like_count', '-published_at'],
                condition=Q(status='published'),
                name='post_trending_idx'
            ),

            # 3. 사용자 게시물 목록
            Index(
                fields=['author', 'status', '-created_at'],
                name='post_author_status_idx'
            ),

            # 4. 전문 검색
            GinIndex(
                fields=['search_vector'],
                name='post_search_idx'
            ),

            # 5. 종합 인기 점수 (커버링 인덱스)
            Index(
                fields=['-like_count'],
                include=['comment_count', 'share_count', 'title'],
                condition=Q(status='published'),
                name='post_engagement_covering_idx'
            ),
        ]

# 쿼리 예시
# 피드 생성
Post.objects.filter(
    author__in=following_users,
    status='published'
).order_by('-published_at')[:20]

# 트렌딩 게시물
Post.objects.filter(
    status='published',
    published_at__gte=timezone.now() - timedelta(days=7)
).order_by('-like_count', '-published_at')[:10]
```

### 예제 3: 예약 시스템

```python
from django.utils import timezone
from django.db.models import Q, F

class Booking(models.Model):
    # 예약 정보
    room = models.ForeignKey('Room', on_delete=models.PROTECT)
    guest = models.ForeignKey(User, on_delete=models.CASCADE)

    # 기간
    check_in = models.DateField()
    check_out = models.DateField()

    # 상태
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('confirmed', 'Confirmed'),
            ('checked_in', 'Checked In'),
            ('checked_out', 'Checked Out'),
            ('cancelled', 'Cancelled'),
        ]
    )

    # 메타
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # 1. 예약 가능한 방 찾기 (날짜 범위 검색)
            Index(
                fields=['room', 'check_in', 'check_out'],
                condition=Q(status__in=['confirmed', 'checked_in']),
                name='booking_availability_idx'
            ),

            # 2. 체크인 예정 목록 (오늘 기준)
            Index(
                fields=['check_in', 'room'],
                condition=Q(
                    status='confirmed',
                    check_in__gte=timezone.now().date()
                ),
                name='upcoming_checkin_idx'
            ),

            # 3. 게스트 예약 내역
            Index(
                fields=['guest', '-check_in'],
                name='guest_booking_history_idx'
            ),

            # 4. 현재 체크인 중인 예약
            Index(
                fields=['room'],
                condition=Q(status='checked_in'),
                name='current_booking_idx'
            ),
        ]

# 예약 가능 여부 확인 쿼리
def is_room_available(room, check_in, check_out):
    conflicting = Booking.objects.filter(
        room=room,
        status__in=['confirmed', 'checked_in'],
        check_in__lt=check_out,
        check_out__gt=check_in
    ).exists()

    return not conflicting
```

---

## 주의사항 및 베스트 프랙티스

### 1. 과도한 인덱스 주의

```python
# ❌ 나쁜 예: 모든 필드에 인덱스
class User(models.Model):
    username = models.CharField(max_length=50, db_index=True)
    email = models.EmailField(db_index=True)
    first_name = models.CharField(max_length=50, db_index=True)  # 불필요
    last_name = models.CharField(max_length=50, db_index=True)   # 불필요
    bio = models.TextField(db_index=True)                        # 텍스트에 인덱스는 비효율
    created_at = models.DateTimeField(db_index=True)             # 거의 사용 안 함

# ✅ 좋은 예: 필요한 인덱스만
class User(models.Model):
    username = models.CharField(max_length=50, unique=True)  # 자동 인덱스
    email = models.EmailField(unique=True)                   # 자동 인덱스
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    bio = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # 실제 사용되는 쿼리에만 인덱스
            Index(fields=['last_name', 'first_name']),  # 이름 검색용
        ]
```

### 2. 인덱스 명명 규칙

```python
class Order(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)

    class Meta:
        indexes = [
            # ✅ 명확한 이름
            Index(
                fields=['customer', 'status'],
                name='order_cust_status_idx'  # 테이블_컬럼들_idx
            ),

            # ❌ 불명확한 이름
            # Index(fields=['customer', 'status'], name='idx1'),
        ]
```

### 3. 마이그레이션 성능 고려

대용량 테이블에 인덱스 추가 시:

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [...]

    operations = [
        # PostgreSQL: CONCURRENTLY 옵션으로 락 없이 인덱스 생성
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY order_status_idx
                ON app_order (status)
                WHERE status IN ('pending', 'processing');
            """,
            reverse_sql="DROP INDEX IF EXISTS order_status_idx;",
        ),
    ]
```

### 4. 인덱스 유지보수

```python
# PostgreSQL: 인덱스 재구축 (조각화 해소)
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 특정 인덱스 재구축
            cursor.execute("REINDEX INDEX order_status_idx;")

            # 테이블 전체 인덱스 재구축
            cursor.execute("REINDEX TABLE app_order;")

            # 데이터베이스 통계 갱신
            cursor.execute("ANALYZE app_order;")
```

### 5. 인덱스 효과 측정

```python
import time
from django.test import TestCase

class IndexPerformanceTest(TestCase):
    def test_query_performance(self):
        # 데이터 준비
        for i in range(10000):
            Order.objects.create(status='pending', customer_id=1)

        # 인덱스 없이 측정
        start = time.time()
        list(Order.objects.filter(status='pending'))
        without_index = time.time() - start

        # 인덱스 추가 (실제로는 마이그레이션으로)
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("CREATE INDEX test_idx ON app_order (status);")

        # 인덱스와 함께 측정
        start = time.time()
        list(Order.objects.filter(status='pending'))
        with_index = time.time() - start

        print(f"Without index: {without_index:.4f}s")
        print(f"With index: {with_index:.4f}s")
        print(f"Improvement: {without_index / with_index:.2f}x")
```

### 6. 일반적인 실수

```python
# ❌ 실수 1: 함수 사용으로 인덱스 무효화
Order.objects.filter(created_at__year=2024)  # EXTRACT(YEAR ...) - 인덱스 사용 불가

# ✅ 올바른 방법
from datetime import date
Order.objects.filter(
    created_at__gte=date(2024, 1, 1),
    created_at__lt=date(2025, 1, 1)
)  # 범위 검색 - 인덱스 사용 가능

# ❌ 실수 2: LIKE '%keyword%' (중간 매칭)
Product.objects.filter(name__contains='phone')  # 인덱스 사용 불가

# ✅ 올바른 방법
Product.objects.filter(name__startswith='phone')  # 인덱스 사용 가능
# 또는 전문 검색 사용

# ❌ 실수 3: OR 조건으로 인덱스 분할
Order.objects.filter(Q(status='pending') | Q(customer=user))  # 비효율적

# ✅ 올바른 방법: 필요시 두 개의 쿼리로 분리
pending = Order.objects.filter(status='pending')
customer_orders = Order.objects.filter(customer=user)
combined = pending | customer_orders  # QuerySet union
```

---

## 요약 체크리스트

### 인덱스 생성 전 확인사항

- [ ] WHERE 절에 자주 사용되는가?
- [ ] JOIN 조건에 사용되는가?
- [ ] ORDER BY에 사용되는가?
- [ ] 카디널리티가 충분한가? (유니크 값이 많은가?)
- [ ] 테이블 크기가 충분히 큰가? (수천 행 이상)
- [ ] 쓰기 작업보다 읽기 작업이 많은가?

### 복합 인덱스 설계 시

- [ ] 왼쪽 접두사 규칙을 고려했는가?
- [ ] 가장 선택적인 컬럼을 앞에 배치했는가?
- [ ] 자주 함께 사용되는 컬럼들인가?
- [ ] 최대 3-4개 컬럼까지만 포함했는가?

### 부분 인덱스 고려 시

- [ ] 대부분의 쿼리가 특정 조건을 포함하는가?
- [ ] 조건에 해당하는 행이 전체의 30% 이하인가?
- [ ] 소프트 삭제 패턴을 사용하는가?
- [ ] NULL 값을 제외할 필요가 있는가?

### 성능 모니터링

- [ ] EXPLAIN ANALYZE로 실행 계획을 확인했는가?
- [ ] 인덱스 사용 통계를 주기적으로 확인하는가?
- [ ] 사용되지 않는 인덱스를 제거하는가?
- [ ] 인덱스 크기를 모니터링하는가?

---

## 참고 자료

### Django 공식 문서
- [Model index reference](https://docs.djangoproject.com/en/stable/ref/models/indexes/)
- [Model Meta options](https://docs.djangoproject.com/en/stable/ref/models/options/)
- [Database optimization](https://docs.djangoproject.com/en/stable/topics/db/optimization/)

### PostgreSQL 문서
- [PostgreSQL Indexes](https://www.postgresql.org/docs/current/indexes.html)
- [Index Types](https://www.postgresql.org/docs/current/indexes-types.html)

### 학습 자료
- Use the Index, Luke! - https://use-the-index-luke.com/
- PostgreSQL Index Advisor
- Django Debug Toolbar (쿼리 분석)

---

**작성일**: 2024
**Django 버전**: 4.2+
**데이터베이스**: PostgreSQL 14+ 기준 (일부 기능)
