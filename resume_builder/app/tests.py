from django.test import TestCase
from users.models import User

class UserTestCase(TestCase):
    def setUp(self):
        # Create a test user before each test
        User.objects.create_user(
            email='testuser@example.com',
            password='password'
        )

    def test_user_creation(self):
        user = User.objects.get(email='testuser@example.com')
        self.assertEqual(user.email, 'testuser@example.com')
        self.assertTrue(user.check_password('password'))