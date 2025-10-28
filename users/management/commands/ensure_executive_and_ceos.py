import os
from typing import Optional, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model

from users.models import Affiliate, Department


User = get_user_model()


CANONICAL_MERBAN = [
	'Finance & Accounts',
	'Government Securities',
	'Pensions & Provident Fund',
	'Private Wealth & Mutual Fund',
	'HR & Admin',
	'Client Service/Marketing',
	'Corporate Finance',
	'IT',
	'Compliance',
	'Audit',
	'Executive',
]


def _env_any(*keys: str) -> Optional[str]:
	for k in keys:
		v = os.environ.get(k)
		if v:
			return v
	return None


def ensure_affiliate(name: str) -> Affiliate:
	aff, _ = Affiliate.objects.get_or_create(name=name, defaults={"description": ""})
	return aff


def ensure_executive_department(affiliate: Affiliate) -> Department:
	# Ensure a single Executive department per affiliate
	dept, created = Department.objects.get_or_create(
		name='Executive',
		affiliate=affiliate,
		defaults={"description": "Executive leadership"}
	)
	return dept


import os
from typing import Optional, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model

from users.models import Affiliate, Department


User = get_user_model()


CANONICAL_MERBAN = [
	'Finance & Accounts',
	'Government Securities',
	'Pensions & Provident Fund',
	'Private Wealth & Mutual Fund',
	'HR & Admin',
	'Client Service/Marketing',
	'Corporate Finance',
	'IT',
	'Compliance',
	'Audit',
]


def _env_any(*keys: str) -> Optional[str]:
	for k in keys:
		v = os.environ.get(k)
		if v:
			return v
	return None


def ensure_affiliate(name: str) -> Affiliate:
	aff, _ = Affiliate.objects.get_or_create(name=name, defaults={"description": ""})
	return aff


def ensure_ceo_for_affiliate(
	affiliate: Affiliate, prefix: str,
	default_email: Optional[str] = None, default_first: Optional[str] = None, default_last: Optional[str] = None,
	default_password: Optional[str] = None
) -> Tuple[User, bool]:
	"""
	Find or create a CEO for given affiliate as individual entity (no Executive department).
	Uses environment variables first: {PREFIX}_CEO_EMAIL, {PREFIX}_CEO_FIRST, etc.
	"""
	# CEO config from env
	email = _env_any(f'{prefix}_CEO_EMAIL', f'{prefix.upper()}_CEO_EMAIL') or default_email
	first = _env_any(f'{prefix}_CEO_FIRST', f'{prefix.upper()}_CEO_FIRST') or default_first
	last = _env_any(f'{prefix}_CEO_LAST', f'{prefix.upper()}_CEO_LAST') or default_last
	username = _env_any(f'{prefix}_CEO_USERNAME', f'{prefix.upper()}_CEO_USERNAME')
	password = _env_any(f'{prefix}_CEO_PASSWORD', f'{prefix.upper()}_CEO_PASSWORD') or default_password

	if not all([email, first, last]):
		raise ValueError(f"Missing CEO data for {prefix}: need email, first, last")

	# Try find by email or username first (more stable)
	user = None
	if email:
		user = User.objects.filter(email=email).first()
	if not user and username:
		user = User.objects.filter(username=username).first()

	created = False
	if user:
		# Update existing user
		updates = {}
		if user.first_name != first:
			updates['first_name'] = first
		if user.last_name != last:
			updates['last_name'] = last
		if user.role != 'ceo':
			updates['role'] = 'ceo'
		# CEOs are individual entities - no specific department assignment needed
		if not user.is_staff:
			updates['is_staff'] = True
		if not user.annual_leave_entitlement:
			updates['annual_leave_entitlement'] = 30
		if updates:
			User.objects.filter(pk=user.pk).update(**updates)
	else:
		# Create new CEO as individual entity
		user = User.objects.create_user(
			username=username or f'{prefix.lower()}_ceo',
			email=email,
			password=password or 'ChangeMe123!',
			first_name=first,
			last_name=last,
			role='ceo',
			department=None,  # CEOs are individual entities
			is_staff=True,
			annual_leave_entitlement=30,
			is_active_employee=True
		)
		created = True

	return user, created


class Command(BaseCommand):
	help = 'Ensure affiliate CEOs as individual entities (no Executive department).'

	def handle(self, *args, **options):
		self.stdout.write('Ensuring affiliate CEOs as individual entities...')
		with transaction.atomic():
			# Ensure affiliates
			merban = ensure_affiliate('MERBAN CAPITAL')
			sdsl = ensure_affiliate('SDSL')
			sbl = ensure_affiliate('SBL')

			# CEOs (SDSL & SBL) as individual entities from env with sensible defaults
			sdsl_user, sdsl_created = ensure_ceo_for_affiliate(
				sdsl, 'SDSL', default_email='sdslceo@umbcapital.com', default_first='Kofi', default_last='Ameyaw',
				default_password=None
			)
			self.stdout.write(self.style.SUCCESS(
				f"✓ SDSL CEO {'created' if sdsl_created else 'updated'}: {sdsl_user.get_full_name()} <{sdsl_user.email}>"
			))

			sbl_user, sbl_created = ensure_ceo_for_affiliate(
				sbl, 'SBL', default_email='sblceo@umbcapital.com', default_first='Winslow', default_last='Sackey',
				default_password=None
			)
			self.stdout.write(self.style.SUCCESS(
				f"✓ SBL CEO {'created' if sbl_created else 'updated'}: {sbl_user.get_full_name()} <{sbl_user.email}>"
			))

			# Optional verification: Merban must have exactly the 10 canonical departments
			names = set(Department.objects.filter(affiliate=merban).values_list('name', flat=True))
			missing = [n for n in CANONICAL_MERBAN if n not in names]
			if missing:
				self.stdout.write(self.style.WARNING(f"! Merban missing canonical departments: {', '.join(missing)}"))
			else:
				self.stdout.write(self.style.SUCCESS('✓ Merban canonical 10 departments present.'))

		self.stdout.write(self.style.SUCCESS('Done ensuring CEOs as individual entities.'))
	# Resolve inputs from env with robust fallbacks
	first = _env_any(f'{prefix}CEO_FIRST_NAME', f'{prefix}_CEO_FIRST_NAME') or default_first
	last = _env_any(f'{prefix}CEO_LAST_NAME', f'{prefix}_CEO_LAST_NAME') or default_last
	email = _env_any(
		f'{prefix}CEO_EMAIL', f'{prefix}_CEO_EMAIL', f'{prefix}CEOemail', f'{prefix}_EMAIL'
	) or default_email
	password = _env_any(
		f'{prefix}CEO_PASSWORD', f'{prefix}_CEO_PASSWORD', f'{prefix}CEOpassword', f'{prefix}_CEOpassword'
	) or default_password

	username = email.split('@')[0] if email else f'{prefix.lower()}_ceo'

	exec_dept = ensure_executive_department(affiliate)

	user = User.objects.filter(email=email).first()
	created = False
	if user:
		# Update existing
		user.first_name = first
		user.last_name = last
		user.username = username or user.username
		setattr(user, 'role', 'ceo')
		if hasattr(user, 'department'):
			setattr(user, 'department', exec_dept)
		user.is_active = True
		user.is_staff = True
		if hasattr(user, 'is_active_employee'):
			setattr(user, 'is_active_employee', True)
		if password:
			user.set_password(password)
		user.save()
	else:
		# Create unique employee_id
		base_emp = f'{prefix.upper()}-CEO'
		emp = base_emp
		if User.objects.filter(employee_id=emp).exists():
			# Find next available with numeric suffix
			i = 2
			while User.objects.filter(employee_id=f'{base_emp}-{i}').exists():
				i += 1
			emp = f'{base_emp}-{i}'
		user = User.objects.create_user(
			username=username or f'{prefix.lower()}_ceo',
			email=email,
			password=password or 'ChangeMe123!',
			first_name=first,
			last_name=last,
			employee_id=emp,
			role='ceo',
			department=exec_dept,
			is_staff=True,
			annual_leave_entitlement=30,
			is_active_employee=True
		)
		created = True

	# Make CEO the HOD of Executive
	if getattr(exec_dept, 'hod_id', None) != user.pk:
		exec_dept.hod = user
		exec_dept.save(update_fields=['hod'])

	return user, created


class Command(BaseCommand):
	help = 'Ensure Executive department per affiliate and provision CEOs for SDSL and SBL.'

	def handle(self, *args, **options):
		self.stdout.write('Ensuring Executive departments and affiliate CEOs...')
		with transaction.atomic():
			# Ensure affiliates
			merban = ensure_affiliate('MERBAN CAPITAL')
			sdsl = ensure_affiliate('SDSL')
			sbl = ensure_affiliate('SBL')

			# Ensure Executive department per affiliate
			for aff in (merban, sdsl, sbl):
				dept = ensure_executive_department(aff)
				self.stdout.write(self.style.SUCCESS(f"✓ Executive department ensured for {aff.name} (id={dept.pk})"))

			# CEOs (SDSL & SBL) from env with sensible defaults
			sdsl_user, sdsl_created = ensure_ceo_for_affiliate(
				sdsl, 'SDSL', default_email='sdslceo@umbcapital.com', default_first='Kofi', default_last='Ameyaw',
				default_password=None
			)
			self.stdout.write(self.style.SUCCESS(
				f"✓ SDSL CEO {'created' if sdsl_created else 'updated'}: {sdsl_user.get_full_name()} <{sdsl_user.email}>"
			))

			sbl_user, sbl_created = ensure_ceo_for_affiliate(
				sbl, 'SBL', default_email='sblceo@umbcapital.com', default_first='Winslow', default_last='Sackey',
				default_password=None
			)
			self.stdout.write(self.style.SUCCESS(
				f"✓ SBL CEO {'created' if sbl_created else 'updated'}: {sbl_user.get_full_name()} <{sbl_user.email}>"
			))

			# Optional verification: Merban must have exactly the 10 canonical departments (Executive may exist additionally)
			names = set(Department.objects.filter(affiliate=merban).values_list('name', flat=True))
			missing = [n for n in CANONICAL_MERBAN if n not in names]
			if missing:
				self.stdout.write(self.style.WARNING(f"! Merban missing canonical departments: {', '.join(missing)}"))
			else:
				self.stdout.write(self.style.SUCCESS('✓ Merban canonical 10 departments present.'))

		self.stdout.write(self.style.SUCCESS('Done ensuring executives and CEOs.'))

