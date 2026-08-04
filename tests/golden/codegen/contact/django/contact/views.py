from common.access.base_views import AuthenticatedAccessAPIView
from common.permissions import AppPermission, AppPermissionChoices
from contact.models import Contact
from contact.serializers import ContactInputSerializer, ContactOutputSerializer
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response


class ContactListView(AuthenticatedAccessAPIView):
	def get(self, request, organization_id: int):
		organization = self.resolve_organization_scope(request, organization_id)

		search = request.query_params.get('search', '').strip()
		status_filter = request.query_params.get('status')

		queryset = organization.contacts

		if search:
			queryset = queryset.filter(Q(email__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search))

		if status_filter:
			valid_statuses = {choice for choice, _ in Contact.StatusChoices.choices}
			if status_filter not in valid_statuses:
				raise ValidationError({'status': 'Select a valid status filter.'})

			queryset = queryset.filter(status=status_filter)

		queryset = queryset.order_by('id')
		serializer = ContactOutputSerializer(queryset, many=True, context={'request': request})
		return Response(serializer.data, status=status.HTTP_200_OK)


class ContactCreateView(AuthenticatedAccessAPIView):
	def post(self, request, organization_id: int):
		organization = self.resolve_organization_scope(request, organization_id)
		self.require_permission(request, AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE), organization=organization)

		edited_data = self.build_serializer_data(request, organization=organization.id)
		serializer = ContactInputSerializer(data=edited_data)
		serializer.is_valid(raise_exception=True)

		instance = serializer.save()
		return Response(ContactOutputSerializer(instance, context={'request': request}).data, status=status.HTTP_201_CREATED)


class ContactDetailView(AuthenticatedAccessAPIView):
	def get(self, request, organization_id: int, contact_id: int):
		_, contact = self.resolve_contact_scope(request, organization_id, contact_id)

		return Response(ContactOutputSerializer(contact, context={'request': request}).data, status=status.HTTP_200_OK)

	def put(self, request, organization_id: int, contact_id: int):
		organization, contact = self.resolve_contact_scope(request, organization_id, contact_id)
		self.require_permission(request, AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE), organization=organization)

		edited_data = self.build_serializer_data(request, organization=organization.id)
		serializer = ContactInputSerializer(contact, data=edited_data, partial=True)
		serializer.is_valid(raise_exception=True)

		instance = serializer.save()
		return Response(ContactOutputSerializer(instance, context={'request': request}).data, status=status.HTTP_200_OK)
