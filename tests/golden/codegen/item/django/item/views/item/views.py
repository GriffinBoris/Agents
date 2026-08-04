from common.access.base_views import AuthenticatedAccessAPIView
from common.permissions import AppPermission, AppPermissionChoices
from django.db.models import Q
from item.models import Item
from item.views.item.serializers import ItemInputSerializer, ItemOutputSerializer
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response


class ItemListView(AuthenticatedAccessAPIView):
	def get(self, request, organization_id: int, workspace_id: int, catalog_entry_id: int):
		_, _, catalog_entry = self.resolve_catalog_entry_scope(request, organization_id, workspace_id, catalog_entry_id)

		search = request.query_params.get('search', '').strip()
		status_filter = request.query_params.get('status')

		queryset = catalog_entry.items

		if search:
			queryset = queryset.filter(Q(name__icontains=search))

		if status_filter:
			valid_statuses = {choice for choice, _ in Item.StatusChoices.choices}
			if status_filter not in valid_statuses:
				raise ValidationError({'status': 'Select a valid status filter.'})

			queryset = queryset.filter(status=status_filter)

		queryset = queryset.order_by('sort_order', 'id')
		serializer = ItemOutputSerializer(queryset, many=True, context={'request': request})
		return Response(serializer.data, status=status.HTTP_200_OK)


class ItemCreateView(AuthenticatedAccessAPIView):
	def post(self, request, organization_id: int, workspace_id: int, catalog_entry_id: int):
		_, workspace, catalog_entry = self.resolve_catalog_entry_scope(request, organization_id, workspace_id, catalog_entry_id)
		self.require_permission(request, AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE), workspace=workspace)

		edited_data = self.build_serializer_data(request, catalog_entry=catalog_entry.id)
		serializer = ItemInputSerializer(data=edited_data)
		serializer.is_valid(raise_exception=True)

		instance = serializer.save()
		return Response(ItemOutputSerializer(instance, context={'request': request}).data, status=status.HTTP_201_CREATED)


class ItemDetailView(AuthenticatedAccessAPIView):
	def get(self, request, organization_id: int, workspace_id: int, catalog_entry_id: int, item_id: int):
		_, _, _, item = self.resolve_item_scope(request, organization_id, workspace_id, catalog_entry_id, item_id)

		return Response(ItemOutputSerializer(item, context={'request': request}).data, status=status.HTTP_200_OK)

	def put(self, request, organization_id: int, workspace_id: int, catalog_entry_id: int, item_id: int):
		_, workspace, catalog_entry, item = self.resolve_item_scope(request, organization_id, workspace_id, catalog_entry_id, item_id)
		self.require_permission(request, AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE), workspace=workspace)

		edited_data = self.build_serializer_data(request, catalog_entry=catalog_entry.id)
		serializer = ItemInputSerializer(item, data=edited_data, partial=True)
		serializer.is_valid(raise_exception=True)

		instance = serializer.save()
		return Response(ItemOutputSerializer(instance, context={'request': request}).data, status=status.HTTP_200_OK)


class ItemArchiveView(AuthenticatedAccessAPIView):
	def post(self, request, organization_id: int, workspace_id: int, catalog_entry_id: int, item_id: int):
		_, workspace, _, item = self.resolve_item_scope(request, organization_id, workspace_id, catalog_entry_id, item_id)
		self.require_permission(request, AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE), workspace=workspace)

		item.status = Item.StatusChoices.INACTIVE
		item.save(update_fields=['status', 'updated_ts'])
		return Response(ItemOutputSerializer(item, context={'request': request}).data, status=status.HTTP_200_OK)
