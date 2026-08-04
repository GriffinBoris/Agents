import pytest
from django.db import IntegrityError
from item.models import Item
from tests.fixtures import FixtureFactory


@pytest.mark.django_db
class TestItemModel:
	def setup_method(self):
		self.organization = FixtureFactory.create_organization()
		self.workspace = FixtureFactory.create_workspace(self.organization)
		self.catalog_entry = FixtureFactory.create_catalog_entry(self.workspace)
		self.item = FixtureFactory.create_item(self.catalog_entry)

	def test_str_returns_name(self):
		assert str(self.item) == self.item.name

	def test_status_defaults_to_active(self):
		assert self.item.status == Item.StatusChoices.ACTIVE

	def test_unique_item_code_per_catalog_entry_is_enforced(self):
		FixtureFactory.create_item(self.catalog_entry, code='duplicate-code')

		with pytest.raises(IntegrityError):
			FixtureFactory.create_item(self.catalog_entry, code='duplicate-code')

	def test_history_log_fields_cover_action_driven_state(self):
		assert Item.history_log_fields == ('status',)
