import pytest
from contact.models import Contact
from contact.serializers import ContactOutputSerializer
from django.urls import reverse
from rest_framework import status
from tenancy.models import OrganizationMembership
from tests.fixtures import FixtureFactory
from workspace.models import WorkspaceMembership


@pytest.mark.django_db
class TestContactViews:
	def setup_method(self):
		self.organization_admin = FixtureFactory.create_user(email='organization-admin@example.com')
		self.workspace_admin = FixtureFactory.create_user(email='workspace-admin@example.com')
		self.workspace_operator = FixtureFactory.create_user(email='workspace-operator@example.com')
		self.other_organization_admin = FixtureFactory.create_user(email='other-organization-admin@example.com')

		self.organization = FixtureFactory.create_organization()
		self.other_organization = FixtureFactory.create_organization()

		FixtureFactory.create_organization_membership(self.organization_admin, self.organization, role=OrganizationMembership.RoleChoices.ADMIN)
		FixtureFactory.create_organization_membership(self.workspace_admin, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
		FixtureFactory.create_workspace_membership(self.workspace_admin, self.workspace, role=WorkspaceMembership.RoleChoices.ADMIN)
		FixtureFactory.create_organization_membership(self.workspace_operator, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
		FixtureFactory.create_workspace_membership(self.workspace_operator, self.workspace, role=WorkspaceMembership.RoleChoices.OPERATOR)
		FixtureFactory.create_organization_membership(self.other_organization_admin, self.other_organization, role=OrganizationMembership.RoleChoices.ADMIN)

		self.contact = FixtureFactory.create_contact(self.organization)
		self.other_contact = FixtureFactory.create_contact(self.other_organization)

		self.list_url = reverse('contact:contact-list', kwargs={'organization_id': self.organization.id})
		self.create_url = reverse('contact:contact-create', kwargs={'organization_id': self.organization.id})
		self.detail_url = reverse('contact:contact-detail', kwargs={'organization_id': self.organization.id, 'contact_id': self.contact.id})

	def test_contact_routes_follow_contract(self):
		assert self.list_url == f'/api/organizations/{self.organization.id}/contacts/list/'
		assert self.create_url == f'/api/organizations/{self.organization.id}/contacts/create/'
		assert self.detail_url == f'/api/organizations/{self.organization.id}/contacts/{self.contact.id}/'

	def test_organization_admin_only_lists_in_scope_contacts(self, client):
		client.force_login(self.organization_admin)

		response = client.get(self.list_url, content_type='application/json')

		expected = ContactOutputSerializer([self.contact], many=True, context={'request': response.wsgi_request}).data
		assert response.status_code == status.HTTP_200_OK
		assert response.json() == expected

	def test_other_organization_admin_cannot_read_contact(self, client):
		client.force_login(self.other_organization_admin)

		response = client.get(self.detail_url, content_type='application/json')

		assert response.status_code == status.HTTP_404_NOT_FOUND

	def test_organization_admin_can_create_contact(self, client):
		client.force_login(self.organization_admin)

		response = client.post(
			self.create_url,
			{
				'email': 'generated@example.com',
				'first_name': 'generated-first-name',
				'last_name': 'generated-last-name',
				'phone': 'generated-phone',
				'status': Contact.StatusChoices.ACTIVE,
				'is_primary': True,
				'notes': 'generated-notes',
			},
			content_type='application/json',
		)

		instance = Contact.objects.get(organization=self.organization, email='Generated Contact')
		expected = ContactOutputSerializer(instance, context={'request': response.wsgi_request}).data
		assert response.status_code == status.HTTP_201_CREATED
		assert response.json() == expected

	def test_create_keeps_route_organization_scope_when_payload_includes_other_organization(self, client):
		client.force_login(self.organization_admin)

		response = client.post(
			self.create_url,
			{
				'email': 'generated@example.com',
				'first_name': 'generated-first-name',
				'last_name': 'generated-last-name',
				'phone': 'generated-phone',
				'status': Contact.StatusChoices.ACTIVE,
				'is_primary': True,
				'notes': 'generated-notes',
				'organization': self.other_organization.id,
			},
			content_type='application/json',
		)

		instance = Contact.objects.get(organization=self.organization, email='Generated Contact')
		assert response.status_code == status.HTTP_201_CREATED
		assert instance.organization_id == self.organization.id

	def test_workspace_operator_cannot_create_contact(self, client):
		client.force_login(self.workspace_operator)

		response = client.post(
			self.create_url,
			{
				'email': 'generated@example.com',
				'first_name': 'generated-first-name',
				'last_name': 'generated-last-name',
				'phone': 'generated-phone',
				'status': Contact.StatusChoices.ACTIVE,
				'is_primary': True,
				'notes': 'generated-notes',
			},
			content_type='application/json',
		)

		assert response.status_code == status.HTTP_403_FORBIDDEN

	def test_other_organization_admin_cannot_create_contact(self, client):
		client.force_login(self.other_organization_admin)

		response = client.post(
			self.create_url,
			{
				'email': 'generated@example.com',
				'first_name': 'generated-first-name',
				'last_name': 'generated-last-name',
				'phone': 'generated-phone',
				'status': Contact.StatusChoices.ACTIVE,
				'is_primary': True,
				'notes': 'generated-notes',
			},
			content_type='application/json',
		)

		assert response.status_code == status.HTTP_404_NOT_FOUND

	def test_organization_admin_can_update_contact(self, client):
		client.force_login(self.organization_admin)

		response = client.put(
			self.detail_url,
			{'email': 'Updated Contact'},
			content_type='application/json',
		)

		self.contact.refresh_from_db()
		expected = ContactOutputSerializer(self.contact, context={'request': response.wsgi_request}).data
		assert response.status_code == status.HTTP_200_OK
		assert response.json() == expected

	def test_workspace_operator_cannot_update_contact(self, client):
		client.force_login(self.workspace_operator)

		response = client.put(
			self.detail_url,
			{'email': 'Updated Contact'},
			content_type='application/json',
		)

		assert response.status_code == status.HTTP_403_FORBIDDEN

	def test_other_organization_admin_cannot_update_contact(self, client):
		client.force_login(self.other_organization_admin)

		response = client.put(
			self.detail_url,
			{'email': 'Updated Contact'},
			content_type='application/json',
		)

		assert response.status_code == status.HTTP_404_NOT_FOUND
