import sys

hammer_name = 'tg-hammer'
hammer_description = 'Helpers for fabric based deployments.'
hammer_version = '0.7.0a1'

__name__ = hammer_name if sys.version_info[0] < 3 else 'hammer'
__description__ = hammer_description
__version__ = hammer_version
