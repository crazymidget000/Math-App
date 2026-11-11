from fractions import Fraction
from secrets import choice
from uuid import UUID

from django.conf import settings
from django.db.models import Count
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .models import ABVisitor

VISITOR_COOKIE = "ab_vid"
VISITOR_COOKIE_MAX_AGE = 365 * 24 * 60 * 60


def visitors_for_cookie(request):
    try:
        visitor_id = UUID(request.COOKIES.get(VISITOR_COOKIE, ""))
    except ValueError:
        return ABVisitor.objects.none()
    return ABVisitor.objects.filter(visitor_id=visitor_id)


@require_GET
@never_cache
def page(request):
    visitor = visitors_for_cookie(request).first()
    is_new = visitor is None
    if is_new:
        visitor = ABVisitor.objects.create(variant=choice(ABVisitor.Variant.values))

    response = render(
        request,
        "abtest/page.html",
        {"variant": visitor.variant, "team_nicknames": settings.AB_TEST_TEAM_NICKNAMES},
    )
    if is_new:
        response.set_cookie(
            VISITOR_COOKIE,
            str(visitor.visitor_id),
            max_age=VISITOR_COOKIE_MAX_AGE,
            path=reverse("abtest:page"),
            httponly=True,
            samesite="Lax",
            secure=settings.SESSION_COOKIE_SECURE,
        )
    return response


@require_POST
def click(request):
    visitors_for_cookie(request).filter(clicked_at__isnull=True).update(clicked_at=timezone.now())
    return HttpResponseRedirect(reverse("abtest:page"), status=303)


@require_GET
@never_cache
def stats(request):
    counts = {variant: {"impressions": 0, "clicks": 0} for variant in ABVisitor.Variant.values}
    rows = ABVisitor.objects.values("variant").annotate(
        impressions=Count("pk"), clicks=Count("clicked_at")
    )
    for row in rows:
        counts[row["variant"]] = {"impressions": row["impressions"], "clicks": row["clicks"]}

    kudos, thanks = counts["kudos"], counts["thanks"]
    kudos_rate = Fraction(kudos["clicks"], max(1, kudos["impressions"]))
    thanks_rate = Fraction(thanks["clicks"], max(1, thanks["impressions"]))
    return JsonResponse({"preferred": "thanks" if thanks_rate > kudos_rate else "kudos", **counts})
