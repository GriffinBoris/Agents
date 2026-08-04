from contact.models import Contact
from rest_framework import serializers


class ContactInputSerializer(serializers.ModelSerializer):
	class Meta:
		model = Contact
		fields = (
			'id',
			'organization',
			'email',
			'first_name',
			'last_name',
			'phone',
			'status',
			'is_primary',
			'notes',
		)
		read_only_fields = ('id',)


class ContactOutputSerializer(serializers.ModelSerializer):
	class Meta:
		model = Contact
		fields = (
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
		)
		read_only_fields = fields
