from django.db import models

# Create your models here.


class AirPollution(models.Model):
    ISIN = models.CharField(max_length=12)
    CompanyName = models.CharField(max_length=200)
    Country = models.CharField(max_length=100)
    Industry = models.CharField(max_length=100)
    Ticker = models.CharField(max_length=100, primary_key=True)

    def __str__(self):
        return self.CompanyName


# Index(['Ticker', 'dates', 'GHG_SCOPE_1', 'GHG_SCOPE_2_LOCATION_BASED',
#    'GHG_SCOPE_2_MARKET_BASED', 'CO2_SCOPE_1', 'CO2_SCOPE_2_LOCATION_BASED',
#    'CO2_SCOPE_2_MARKET_BASED', 'SCOPE_2_GHG_CO2_EMISSIONS',
#    'SCOPE_1_GHG_CO2_EMISSIONS'],
class AirPollutionData(models.Model):
    airPollution = models.ForeignKey(
        AirPollution, on_delete=models.CASCADE, related_name="ticker"
    )
    dates = models.DateField()
    GHG_SCOPE_1 = models.FloatField(null=True)
    GHG_SCOPE_2_LOCATION_BASED = models.FloatField(null=True)
    GHG_SCOPE_2_MARKET_BASED = models.FloatField(null=True)
    CO2_SCOPE_1 = models.FloatField(null=True)
    CO2_SCOPE_2_LOCATION_BASED = models.FloatField(null=True)
    CO2_SCOPE_2_MARKET_BASED = models.FloatField(null=True)
    SCOPE_2_GHG_CO2_EMISSIONS = models.FloatField(null=True)
    SCOPE_1_GHG_CO2_EMISSIONS = models.FloatField(null=True)

    def __str__(self):
        return self.airPollution.Ticker + "|" + str(self.dates)


class CompanyReport(models.Model):
    symbol = models.CharField(max_length=10)
    security = models.CharField(max_length=200, primary_key=True)
    gics_sector = models.CharField(max_length=100, null=True, blank=True)
    gics_industry = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.security

    class Meta:
        verbose_name = "Company Report"
        verbose_name_plural = "Company Reports"


class CompanyReportData(models.Model):
    id = models.AutoField(primary_key=True)
    symbol = models.CharField(
        max_length=10
    )  # Assuming max length 10 for symbols like 'GOOGL'
    security = models.CharField(max_length=200)
    gics_sector = models.CharField(max_length=100, null=True, blank=True)
    gics_industry = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)
    report_url = models.URLField(
        max_length=500, null=True, blank=True
    )  # Increased max_length for potentially long URLs
    report_year = models.IntegerField(null=True, blank=True)
    annual_carbon_emissions = models.FloatField(null=True, blank=True)  # tonnes co₂
    annual_water_consumption = models.FloatField(null=True, blank=True)  # cubic meters
    renewable_energy_usage = models.FloatField(null=True, blank=True)  # mwh
    sustainable_materials_usage_ratio = models.FloatField(
        null=True, blank=True
    )  # percent
    waste_recycling_rate = models.FloatField(null=True, blank=True)  # percent

    def __str__(self):
        return f"{self.security} ({self.symbol}) - {self.report_year}"

    class Meta:
        # Optional: Add constraints if needed, e.g., unique together for symbol and year
        # unique_together = ('symbol', 'report_year',)
        verbose_name = "Company Report Data"
        verbose_name_plural = "Company Report Data"
