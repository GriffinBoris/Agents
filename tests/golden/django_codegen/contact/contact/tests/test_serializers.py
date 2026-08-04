import pytest
from contact.models import Contact
from contact.serializers import ContactInputSerializer, ContactOutputSerializer
from tests.fixtures import FixtureFactory


@pytest.mark.django_db
class TestContactInputSerializer:
	def setup_method(self):
		self.organization = FixtureFactory.create_organization()
		self.payload = {
			'email': 'generated@example.com',
			'first_name': 'generated-first-name',
			'last_name': 'generated-last-name',
			'phone': 'generated-phone',
			'status': Contact.StatusChoices.ACTIVE,
			'is_primary': True,
			'notes': 'generated-notes',
			'organization': self.organization.id,
		}

	def test_valid_payload_creates_contact(self):
		serializer = ContactInputSerializer(data=self.payload)

		assert serializer.is_valid(), serializer.errors

		instance = serializer.save()
		assert instance.organization_id == self.organization.id
		assert instance.email == 'generated@example.com'

	def test_email_is_required(self):
		payload = dict(self.payload)
		payload.pop('email')

		serializer = ContactInputSerializer(data=payload)

		assert not serializer.is_valid()
		assert 'email' in serializer.errors


@pytest.mark.django_db
class TestContactOutputSerializer:
	def setup_method(self):
		self.organization = FixtureFactory.create_organization()
		self.contact = FixtureFactory.create_contact(self.organization)

	def test_output_shape_is_exact(self):
		data = ContactOutputSerializer(self.contact).data

		assert set(data.keys()) == {
			'id',
			'organization',
			'email',
			'first_name',
			'last_name',
			'phone',
			'status',
			'is_primary',
			'notes',
			'created_ts',
			'updated_ts',
		}
		assert data['id'] == self.contact.id
		assert data['email'] == self.contact.email
