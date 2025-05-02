import csv
import datetime
import decimal
import json

from django.contrib.auth import logout
from django.contrib.auth.views import (
    LoginView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetView,
)
from django.http import HttpResponse
from django.shortcuts import redirect, render
from theme_pixel.forms import (
    RegistrationForm,
    UserLoginForm,
    UserPasswordChangeForm,
    UserPasswordResetForm,
    UserSetPasswordForm,
)
from theme_pixel.models import (
    AirPollution,
    AirPollutionData,
    CompanyReport,
    CompanyReportData,
)


# Create your views here.
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        # 处理返回数据中有date类型的数据
        if isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        # 处理返回数据中有datetime类型的数据
        elif isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        # 处理返回数据中有decimal类型的数据
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        else:
            return json.JSONEncoder.default(self, obj)


# Pages
def index(request):
    return render(request, "pages/index.html")


def abouts_us(request):
    return render(request, "pages/about.html")


def contact_us(request):
    return render(request, "pages/contact.html")


def landing_freelancer(request):
    return render(request, "pages/landing-freelancer.html")


def blank_page(request):
    return render(request, "pages/blank.html")


# Authentication
class UserLoginView(LoginView):
    template_name = "accounts/sign-in.html"
    form_class = UserLoginForm


def logout_view(request):
    logout(request)
    return redirect("/accounts/login")


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            print("Account created successfully!")
            return redirect("/accounts/login")
        else:
            print("Registration failed!")
    else:
        form = RegistrationForm()

    context = {"form": form}
    return render(request, "accounts/sign-up.html", context)


class UserPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    form_class = UserPasswordResetForm


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    form_class = UserSetPasswordForm


class UserPasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change.html"
    form_class = UserPasswordChangeForm


# search
def tables(request):
    if request.method == "GET":
        Industry = request.GET.get("Industry")
        Security = request.GET.get("Security")
        results = []  # Initialize results as an empty list

        if Industry:
            results = CompanyReport.objects.filter(gics_industry__icontains=Industry)
        elif Security:
            results = CompanyReport.objects.filter(security__icontains=Security)
        # If neither Industry nor Security is provided, results remains an empty list

        content = {"results": results}
        return render(request, "components/tables.html", content)


# details
def details(request):
    if request.method == "GET":
        security = request.GET.get("security")
        results = []  # Initialize results as an empty list
        if security:
            # Query CompanyReportData based on security
            results = CompanyReportData.objects.filter(
                security__iexact=security
            )  # Use iexact for case-insensitive match
        # Always pass results (even if empty) to the template
        content = {"results": results}
        return render(request, "components/details.html", content)


# filter
def filter(request):
    if request.method == "GET":
        security = request.GET.get("Security")
        query = CompanyReportData.objects.all()
        if security:
            query = query.filter(security__icontains=security)
        query = query[:100]

        if request.GET.get("download"):
            response = HttpResponse(content_type="text/csv")
            response[
                "Content-Disposition"
            ] = 'attachment; filename="company_report_data.csv"'
            writer = csv.writer(response)
            writer.writerow(
                [
                    "Security",
                    "Report URL",
                    "Report Year",
                    "Annual Carbon Emissions (tCO₂)",
                    "Annual Water Consumption (m³)",
                    "Renewable Energy Usage (MWh)",
                    "Sustainable Materials Usage (%)",
                    "Waste Recycling Rate (%)",
                ]
            )
            for data in query:
                writer.writerow(
                    [
                        data.security,
                        data.report_url,
                        data.report_year,
                        data.annual_carbon_emissions,
                        data.annual_water_consumption,
                        data.renewable_energy_usage,
                        data.sustainable_materials_usage_ratio,
                        data.waste_recycling_rate,
                    ]
                )
            return response

        results = []
        col_security_set = set()
        col_report_year_set = set()
        for data in query:
            results.append(
                {
                    "security": data.security,
                    "report_url": data.report_url,
                    "report_year": data.report_year,
                    "annual_carbon_emissions": data.annual_carbon_emissions,
                    "annual_water_consumption": data.annual_water_consumption,
                    "renewable_energy_usage": data.renewable_energy_usage,
                    "sustainable_materials_usage_ratio": data.sustainable_materials_usage_ratio,
                    "waste_recycling_rate": data.waste_recycling_rate,
                }
            )
            col_security_set.add(data.security)
            col_report_year_set.add(data.report_year)
        col_security = [{"text": col, "value": col} for col in col_security_set]
        col_report_year = [{"text": col, "value": col} for col in col_report_year_set]
        content = {
            "results": json.dumps(results, ensure_ascii=False, cls=DateEncoder),
            "col_security": json.dumps(col_security, ensure_ascii=False),
            "col_report_year": json.dumps(col_report_year, ensure_ascii=False),
        }
        return render(request, "components/filter.html", content)


# chart
def chart(request):
    from pyecharts import options as opts
    from pyecharts.charts import Bar

    if request.method == "GET":
        security = request.GET.get("security")
        if security:
            results = CompanyReportData.objects.filter(security__iexact=security)
            if results:
                attr = []
                v1 = []
                v2 = []
                v3 = []
                v4 = []
                title = str(results[0].security)

                for result in results:
                    attr.append(str(result.report_year))
                    v1.append(result.annual_carbon_emissions)
                    v2.append(result.annual_water_consumption)
                    v3.append(result.renewable_energy_usage)
                    v4.append(result.waste_recycling_rate)

                bar = Bar()
                bar.width = "100%"
                bar.add_xaxis(attr)
                bar.add_yaxis("Annual Carbon Emissions (tons CO₂)", v1)
                bar.add_yaxis("Annual Water Consumption (cubic meters)", v2)
                bar.add_yaxis("Renewable Energy Usage (MWh)", v3)
                bar.add_yaxis("Waste Recycling Rate (%)", v4)
                bar.set_global_opts(
                    title_opts=opts.TitleOpts(title=title),
                    tooltip_opts=opts.TooltipOpts(trigger="axis"),
                    toolbox_opts=opts.ToolboxOpts(is_show=True),
                    datazoom_opts=opts.DataZoomOpts(),
                )

                bar.render(path="theme_pixel/templates/components/chart.html")
                return render(
                    request, "components/chart.html", {"chart": bar.render_embed()}
                )

        else:
            results = []
            content = {"results": results}
        return render(request, "components/chart.html", content)


# Components
def accordion(request):
    return render(request, "components/accordions.html")


def alerts(request):
    return render(request, "components/alerts.html")


def badges(request):
    return render(request, "components/badges.html")


def bootstrap_carousels(request):
    return render(request, "components/bootstrap-carousels.html")


def breadcrumbs(request):
    return render(request, "components/breadcrumbs.html")


def buttons(request):
    return render(request, "components/buttons.html")


def cards(request):
    return render(request, "components/cards.html")


def dropdowns(request):
    return render(request, "components/dropdowns.html")


def forms(request):
    return render(request, "components/forms.html")


def modals(request):
    return render(request, "components/modals.html")


def navs(request):
    return render(request, "components/navs.html")


def pagination(request):
    return render(request, "components/pagination.html")


def popovers(request):
    return render(request, "components/popovers.html")


def progress_bars(request):
    return render(request, "components/progress-bars.html")


def tabs(request):
    return render(request, "components/tabs.html")


def toasts(request):
    return render(request, "components/toasts.html")


def tooltips(request):
    return render(request, "components/tooltips.html")


def typography(request):
    return render(request, "components/typography.html")
