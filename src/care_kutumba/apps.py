from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

PLUGIN_NAME = "care_kutumba"


class Care_kutumbaConfig(AppConfig):
    name = PLUGIN_NAME
    verbose_name = _("Care_kutumba")

    def ready(self):
        import care_kutumba.signals  # noqa F401
