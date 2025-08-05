from django.contrib import admin
from django.template.response import TemplateResponse
from django import forms

from bot.models import TelegramUser
from bot.constants import REGIONS


class DashboardFilterForm(forms.Form):
    region = forms.ChoiceField(choices=REGIONS, required=False)


def custom_admin_index(request):
    form = DashboardFilterForm(request.GET or None)
    users = TelegramUser.objects.all()

    if form.is_valid():
        
        region = form.cleaned_data.get("region")

        if region:
            users = users.filter(region=region)

    context = dict(
        admin.site.each_context(request),
        title="Dashboard",
        form=form,
        registered_count=users.count(),
        paid_count=users.filter(is_confirmed=True).count(),
        unpaid_count=users.filter(is_confirmed=False).count(),
    )
    return TemplateResponse(request, "admin/custom_index.html", context)
