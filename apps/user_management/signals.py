"""
UserProfile no longer has a relation to django.contrib.auth.User.

This module is intentionally kept free of signal receivers so older imports of
apps.user_management.signals do not create invalid UserProfile records.
"""
