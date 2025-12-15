from typing import ClassVar

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Meta:
        db_table: ClassVar[str] = "user"
        verbose_name: ClassVar[str] = "user"
        verbose_name_plural: ClassVar[str] = "users"
