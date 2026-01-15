# users/models.py
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # Avoid clashes with default auth.User
    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_set",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups"
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions_set",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions"
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # No additional fields required for superuser

    def __str__(self):
        return self.email
    
    def get_display_name(self):
        """
        Get display name for greetings - use full_name if available, 
        otherwise email prefix.
        
        Returns:
            str: Display name for the user
        """
        if self.full_name and self.full_name.strip():
            return self.full_name.strip()
        
        # Fallback to email username (part before @)
        if '@' in self.email:
            return self.email.split('@')[0]
        
        return self.email

    # ---------------- Plan Helpers ----------------
    @property
    def current_plan(self):
        """
        Returns the latest Plan instance assigned to the user.
        Returns None if no plan exists.
        """
        return self.plans.last()  # 'plans' is the related_name in Plan model

    @property
    def plan_type(self):
        """
        Returns the plan_type of the user's latest plan.
        Defaults to 'free' if no plan is assigned.
        """
        plan = self.current_plan
        return plan.plan_type if plan else "free"