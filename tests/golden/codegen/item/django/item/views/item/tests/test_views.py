import pytest
from django.urls import reverse
from item.models import Item
from item.views.item.serializers import ItemOutputSerializer
from rest_framework import status
from tenancy.models import OrganizationMembership
from tests.fixtures import FixtureFactory
from workspace.models import WorkspaceMembership


@pytest.mark.django_db
class TestItemViews:
	def setup_method(self):
		self.organization_admin = FixtureFactory.create_user(email='organization-admin@example.com')
		self.workspace_admin = FixtureFactory.create_user(email='workspace-admin@example.com')
		self.workspace_operator = FixtureFactory.create_user(email='workspace-operator@example.com')
		self.other_organization_admin = FixtureFactory.create_user(email='other-organization-admin@example.com')

		self.organization = FixtureFactory.create_organization()
		self.other_organization = FixtureFactory.create_organization()
		self.workspace = FixtureFactory.create_workspace(self.organization)
		self.other_workspace = FixtureFactory.create_workspace(self.other_organization)
		self.catalog_entry = FixtureFactory.create_catalog_entry(self.workspace)
		self.other_catalog_entry = FixtureFactory.create_catalog_entry(self.other_workspace)

		FixtureFactory.create_organization_membership(self.organization_admin, self.organization, role=OrganizationMembership.RoleChoices.ADMIN)
		FixtureFactory.create_organization_membership(self.workspace_admin, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
		FixtureFactory.create_workspace_membership(self.workspace_admin, self.workspace, role=WorkspaceMembership.RoleChoices.ADMIN)
		FixtureFactory.create_organization_membership(self.workspace_operator, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
		FixtureFactory.create_workspace_membership(self.workspace_operator, self.workspace, role=WorkspaceMembership.RoleChoices.OPERATOR)
		FixtureFactory.create_organization_membership(self.other_organization_admin, self.other_organization, role=OrganizationMembership.RoleChoices.ADMIN)

		self.item = FixtureFactory.create_item(self.catalog_entry)
		self.other_item = FixtureFactory.create_item(self.other_catalog_entry)

		self.list_url = reverse('workspace:catalog_entry:item:item-list', kwargs={'organization_id': self.organization.id, 'workspace_id': self.workspace.id, 'catalog_entry_id': self.catalog_entry.id})
		self.create_url = reverse('workspace:catalog_entry:item:item-create', kwargs={'organization_id': self.organization.id, 'workspace_id': self.workspace.id, 'catalog_entry_id': self.catalog_entry.id})
		self.detail_url = reverse('workspace:catalog_entry:item:item-detail', kwargs={'organization_id': self.organization.id, 'workspace_id': self.workspace.id, 'catalog_entry_id': self.catalog_entry.id, 'item_id': self.item.id})
		self.archive_url = reverse('workspace:catalog_entry:item:item-archive', kwargs={'organization_id': self.organization.id, 'workspace_id': self.workspace.id, 'catalog_entry_id': self.catalog_entry.id, 'item_id': self.item.id})

	def test_item_routes_follow_contract(self):
		assert self.list_url == f'/api/organizations/{self.organization.id}/workspaces/{self.workspace.id}/catalog-entries/{self.catalog_entry.id}/items/list/'
		assert self.create_url == f'/api/organizations/{self.organization.id}/workspaces/{self.workspace.id}/catalog-entries/{self.catalog_entry.id}/items/create/'
		assert self.detail_url == f'/api/organizations/{self.organization.id}/workspaces/{self.workspace.id}/catalog-entries/{self.catalog_entry.id}/items/{self.item.id}/'
		assert self.archive_url == f'/api/organizations/{self.organization.id}/workspaces/{self.workspace.id}/catalog-entries/{self.catalog_entry.id}/items/{self.item.id}/archive/'

	def test_organization_admin_only_lists_in_scope_items(self, client):
		client.force_login(self.organization_admin)

		response = client.get(self.list_url, content_type='application/json')

		expected = ItemOutputSerializer([self.item], many=True, context={'request': response.wsgi_request}).data
		assert response.status_code == status.HTTP_200_OK
		assert response.json() == expected

	def test_other_organization_admin_cannot_read_item(self, client):
		client.force_login(self.other_organization_admin)

		response = client.get(self.detail_url, content_type='application/json')

		assert response.status_code == status.HTTP_404_NOT_FOUND

	def test_organization_admin_can_create_item(self, client):
		client.force_login(self.organization_admin)

		response = client.post(
			self.create_url,
			{
				'name': 'Generated Item',
				'code': 'generated-code',
				'summary': 'generated-summary',
				'sort_order': 1,
			},
			content_type='application/json',
		)

		instance = Item.objects.get(catalog_entry=self.catalog_entry, name='Generated Item')
		expected = ItemOutputSerializer(instance, context={'request': response.wsgi_request}).data
		assert response.status_code == status.HTTP_201_CREATED
		assert response.json() == expected

	def test_create_keeps_route_catalog_entry_scope_when_payload_includes_other_catalog_entry(self, client):
		client.force_login(self.organization_admin)

		response = client.post(
			self.create_url,
			{
				'name': 'Generated Item',
				'code': 'generated-code',
				'summary': 'generated-summary',
				'sort_order': 1,
				'catalog_entry': self.other_catalog_entry.id,
			},
			content_type='application/json',
		)

		instance = Item.objects.get(catalog_entry=self.catalog_entry, name='Generated Item')
		assert response.status_code == status.HTTP_201_CREATED
		assert instance.catalog_entry_id == self.catalog_entry.id

	def test_workspace_operator_cannot_create_item(self, client):
		client.force_login(self.workspace_operator)

		response = client.post(
			self.create_url,
			{
				'name': 'Generated Item',
				'code': 'generated-code',
				'summary': 'generated-summary',
				'sort_order': 1,
			},
			content_type='application/json',
		)

		assert response.status_code == status.HTTP_403_FORBIDDEN

	def test_other_organization_admin_cannot_create_item(self, client):
		client.force_login(self.other_organization_admin)

		response = client.post(
			self.create_url,
			{
				'name': 'Generated Item',
				'code': 'generated-code',
				'summary': 'generated-summary',
				'sort_order': 1,
			},
			content_type='application/json',
		)

		assert response.status_code == status.HTTP_404_NOT_FOUND

	def test_organization_admin_can_update_item(self, client):
		client.force_login(self.organization_admin)

		response = client.put(
			self.detail_url,
			{'name': 'Updated Item'},
			content_type='application/json',
		)

		self.item.refresh_from_db()
		expected = ItemOutputSerializer(self.item, context={'request': response.wsgi_request}).data
		assert response.status_code == status.HTTP_200_OK
		assert response.json() == expected

	def test_workspace_operator_cannot_update_item(self, client):
		client.force_login(self.workspace_operator)

		response = client.put(
			self.detail_url,
			{'name': 'Updated Item'},
			content_type='application/json',
		)

		assert response.status_code == status.HTTP_403_FORBIDDEN

	def test_other_organization_admin_cannot_update_item(self, client):
		client.force_login(self.other_organization_admin)

		response = client.put(
			self.detail_url,
			{'name': 'Updated Item'},
			content_type='application/json',
		)

		assert response.status_code == status.HTTP_404_NOT_FOUND

	def test_generic_update_cannot_change_status(self, client):
		client.force_login(self.organization_admin)

		response = client.put(
			self.detail_url,
			{'status': Item.StatusChoices.INACTIVE},
			content_type='application/json',
		)

		assert response.status_code == status.HTTP_400_BAD_REQUEST

	def test_organization_admin_can_archive_item(self, client):
		client.force_login(self.organization_admin)

		response = client.post(self.archive_url, content_type='application/json')

		self.item.refresh_from_db()
		assert response.status_code == status.HTTP_200_OK
		assert self.item.status == Item.StatusChoices.INACTIVE

	def test_workspace_operator_cannot_archive_item(self, client):
		client.force_login(self.workspace_operator)

		response = client.post(self.archive_url, content_type='application/json')

		assert response.status_code == status.HTTP_403_FORBIDDEN

	def test_other_organization_admin_cannot_archive_item(self, client):
		client.force_login(self.other_organization_admin)

		response = client.post(self.archive_url, content_type='application/json')

		assert response.status_code == status.HTTP_404_NOT_FOUND
