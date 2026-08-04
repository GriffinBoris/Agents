from typing import Optional

from contact.models import Contact
from core.utility import random_string
from tenancy.models import Organization


class FixtureFactory:
	@staticmethod
	def create_contact(
		organization: Organization,
		email: Optional[str] = None,
		first_name: str = '',
		last_name: str = '',
		phone: str = '',
		status: str = Contact.StatusChoices.ACTIVE,
		is_primary: bool = false,
		notes: str = '',
	):
		email = email or f'Contact {random_string()}'
		return Contact.objects.create(
			organization=organization,
			email=email,
			first_name=first_name,
			last_name=last_name,
			phone=phone,
			status=status,
			is_primary=is_primary,
			notes=notes,
		)
