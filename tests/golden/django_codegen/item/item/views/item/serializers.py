from item.models import Item
from rest_framework import serializers


class ItemInputSerializer(serializers.ModelSerializer):
	class Meta:
		model = Item
		fields = (
			'id',
			'catalog_entry',
			'name',
			'code',
			'status',
			'summary',
			'sort_order',
		)
		read_only_fields = ('id',)

	def validate(self, attrs):
		attrs = super().validate(attrs)

		if self.instance and 'status' in attrs:
			raise serializers.ValidationError({'status': 'Use the item archive action to change status.'})

		return attrs


class ItemOutputSerializer(serializers.ModelSerializer):
	class Meta:
		model = Item
		fields = (
			'id',
			'catalog_entry',
			'name',
			'code',
			'status',
			'summary',
			'sort_order',
			'created_ts',
			'updated_ts',
		)
		read_only_fields = fields
