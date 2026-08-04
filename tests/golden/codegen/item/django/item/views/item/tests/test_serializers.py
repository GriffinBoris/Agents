import pytest
from item.models import Item
from item.views.item.serializers import ItemInputSerializer, ItemOutputSerializer
from tests.fixtures import FixtureFactory


@pytest.mark.django_db
class TestItemInputSerializer:
	def setup_method(self):
		self.organization = FixtureFactory.create_organization()
		self.workspace = FixtureFactory.create_workspace(self.organization)
		self.catalog_entry = FixtureFactory.create_catalog_entry(self.workspace)
		self.payload = {
			'name': 'Generated Item',
			'code': 'generated-code',
			'summary': 'generated-summary',
			'sort_order': 1,
			'catalog_entry': self.catalog_entry.id,
		}

	def test_valid_payload_creates_item(self):
		serializer = ItemInputSerializer(data=self.payload)

		assert serializer.is_valid(), serializer.errors

		instance = serializer.save()
		assert instance.catalog_entry_id == self.catalog_entry.id
		assert instance.name == 'Generated Item'

	def test_name_is_required(self):
		payload = dict(self.payload)
		payload.pop('name')

		serializer = ItemInputSerializer(data=payload)

		assert not serializer.is_valid()
		assert 'name' in serializer.errors

	def test_status_cannot_change_through_generic_update(self):
		instance = FixtureFactory.create_item(self.catalog_entry)

		serializer = ItemInputSerializer(instance, data={'status': Item.StatusChoices.INACTIVE}, partial=True)

		assert not serializer.is_valid()
		assert 'status' in serializer.errors


@pytest.mark.django_db
class TestItemOutputSerializer:
	def setup_method(self):
		self.organization = FixtureFactory.create_organization()
		self.workspace = FixtureFactory.create_workspace(self.organization)
		self.catalog_entry = FixtureFactory.create_catalog_entry(self.workspace)
		self.item = FixtureFactory.create_item(self.catalog_entry)

	def test_output_shape_is_exact(self):
		data = ItemOutputSerializer(self.item).data

		assert set(data.keys()) == {
			'id',
			'catalog_entry',
			'name',
			'code',
			'status',
			'summary',
			'sort_order',
			'created_ts',
			'updated_ts',
		}
		assert data['id'] == self.item.id
		assert data['name'] == self.item.name
