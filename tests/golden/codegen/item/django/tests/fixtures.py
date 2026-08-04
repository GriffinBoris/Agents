from typing import Optional

from catalog_entry.models import CatalogEntry
from core.utility import random_string
from item.models import Item


class FixtureFactory:
	@staticmethod
	def create_item(
		catalog_entry: CatalogEntry,
		name: Optional[str] = None,
		code: Optional[str] = None,
		status: str = Item.StatusChoices.ACTIVE,
		summary: str = '',
		sort_order: int = 0,
	):
		name = name or f'Item {random_string()}'
		code = code or random_string()
		return Item.objects.create(
			catalog_entry=catalog_entry,
			name=name,
			code=code,
			status=status,
			summary=summary,
			sort_order=sort_order,
		)
