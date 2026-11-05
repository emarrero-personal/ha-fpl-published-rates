"""Constants for FPL Published Rates."""

from datetime import timedelta

DOMAIN = "fpl_rates"
PLATFORMS = ["sensor", "binary_sensor", "button"]

DEFAULT_NAME = "FPL Published Rates"
DEFAULT_RATES_PAGE = "https://www.fpl.com/rates.html"
DEFAULT_PDF_URL = (
    "https://www.fpl.com/content/dam/fplgp/us/en/rates/pdf/"
    "res-eff-jan-2026.pdf"
)
DEFAULT_UPDATE_HOURS = 24
MIN_UPDATE_HOURS = 6
MAX_UPDATE_HOURS = 168

CONF_NAME = "name"
CONF_RATES_PAGE = "rates_page"
CONF_PDF_URL = "pdf_url"
CONF_AUTO_DISCOVER = "auto_discover"
CONF_UPDATE_HOURS = "update_hours"
CONF_MONTHLY_ENERGY_ENTITY = "monthly_energy_entity"

CURRENCY_PER_KWH = "$/kWh"
CENTS_PER_KWH = "¢/kWh"
DEFAULT_UPDATE_INTERVAL = timedelta(hours=DEFAULT_UPDATE_HOURS)
