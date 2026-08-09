from django.apps import AppConfig


class AgentsChecksConfig(AppConfig):
    name = 'agents.rules.django_checks'
    verbose_name = 'Agents repository checks'

    def ready(self) -> None:
        from agents.rules.django_checks import checks  # noqa: F401
