from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model

from services.external_api import check_hometax_registration
from services.calculation import calculate_refund

User = get_user_model()


@login_required
@require_http_methods(["GET"])
def process_refund(request):
    """환급 처리 전체 플로우"""
    user_id = request.user.id

    try:
        # 1. 홈택스 가입 확인
        hometax_status = check_hometax_registration(user_id)

        # 2. 환급액 계산
        refund_amount = calculate_refund(user_id)

        return JsonResponse(
            {
                "success": True,
                "user": request.user.username,
                "hometax_status": hometax_status,
                "refund_amount": refund_amount,
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": "UNKNOWN_ERROR", "message": str(e)}, status=500
        )
