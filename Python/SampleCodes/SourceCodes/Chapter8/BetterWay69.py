# Better Way 69 정확도가 매우 중요한 경우에는 decimal을 사용하라

from decimal import Decimal, ROUND_UP

rate = 1.45
seconds = 3 * 60 + 42
cost = rate * seconds / 60
print(cost)
# 5.364999999999999
print(round(cost, 2))
# 5.36

rate = Decimal("1.45")
seconds = Decimal(3 * 60 + 42)
cost = rate * seconds / Decimal(60)
print(cost)
# 5.365

print(Decimal("1.45"))
print(Decimal(1.45))
# 1.45
# 1.4499999999999999555910790149937383830547332763671875

rounded = cost.quantize(Decimal("0.01"), rounding=ROUND_UP)
print(f"반올림 전: {cost} 반올림 후: {rounded}")
# 반올림 전: 5.365 반올림 후: 5.37
