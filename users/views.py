import json

from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt  # Relax for API clients; tighten if using CSRF protection
@require_POST
def login_view(request):
    """
    Log in a user given a username and password.

    Accepts:
      - JSON: {"username": "...", "password": "..."}
      - Or form-encoded: username=...&password=...

    Response:
      - 200 with basic user info on success
      - 400 if credentials are missing/invalid
    """

    if request.content_type == "application/json":
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON body."}, status=400)
        username = data.get("username")
        password = data.get("password")
    else:
        username = request.POST.get("username")
        password = request.POST.get("password")

    if not username or not password:
        return JsonResponse(
            {"detail": "Both 'username' and 'password' are required."}, status=400
        )

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse(
            {"detail": "Invalid username or password."},
            status=400,
        )

    login(request, user)

    return JsonResponse(
        {
            "id": user.id,
            "username": user.get_username(),
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        },
        status=200,
    )
