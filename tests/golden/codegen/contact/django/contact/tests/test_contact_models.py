import pytest
from contact.models import Contact
from tests.fixtures import FixtureFactory


@pytest.mark.django_db
class TestContactModel:
	def setup_method(self):
		self.organization = FixtureFactory.create_organization()
		self.contact = FixtureFactory.create_contact(self.organization)

	def test_str_returns_email(self):
		assert str(self.contact) == self.contact.email

	def test_status_defaults_to_active(self):
		assert self.contact.status == Contact.StatusChoices.ACTIVE
