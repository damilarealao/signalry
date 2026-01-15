# users/tests.py
from django.test import TestCase
from .models import User
from django.contrib.auth.models import Group, Permission
from plans.models import Plan

class UserModelTests(TestCase):

    def test_create_user(self):
        user = User.objects.create_user(email="user@test.com", password="secure123")
        self.assertEqual(user.email, "user@test.com")
        self.assertTrue(user.check_password("secure123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="admin@test.com", password="admin123")
        self.assertEqual(admin.email, "admin@test.com")
        self.assertTrue(admin.check_password("admin123"))
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_email_unique_constraint(self):
        User.objects.create_user(email="unique@test.com", password="pass123")
        with self.assertRaises(Exception):
            User.objects.create_user(email="unique@test.com", password="pass123")

    def test_groups_assignment(self):
        group = Group.objects.create(name="Test Group")
        user = User.objects.create_user(email="group@test.com", password="pass123")
        user.groups.add(group)
        self.assertIn(group, user.groups.all())

    def test_permissions_assignment(self):
        perm = Permission.objects.first()  # pick any permission
        user = User.objects.create_user(email="perm@test.com", password="pass123")
        user.user_permissions.add(perm)
        self.assertIn(perm, user.user_permissions.all())

    def test_premium_plan_assignment(self):
        # Assign a plan to the user
        user = User.objects.create_user(email="premium@test.com", password="pass123")
        Plan.objects.create_plan_for_user(user, "premium")
        plan = user.plans.first()
        self.assertIsNotNone(plan)
        self.assertEqual(plan.plan_type, "premium")  # updated from plan.name -> plan.plan_type

    def test_str_method(self):
        user = User.objects.create_user(email="str@test.com", password="pass123")
        self.assertEqual(str(user), "str@test.com")
