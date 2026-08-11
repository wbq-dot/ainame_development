import unittest

from pydantic import ValidationError

from schemas.user_schemas import LoginIn, RegisterIn, UserSchema


class LocalExpertLoginSchemaTests(unittest.TestCase):
    def test_local_demo_email_can_login_and_serialize(self):
        login = LoginIn(
            email="ordinary.expert@example.local",
            password="DemoExpert29!",
        )
        user = UserSchema(
            id=1,
            email=login.email,
            username="ordinary_expert",
            role="expert",
            status="active",
        )
        self.assertEqual("ordinary.expert@example.local", user.email)

    def test_registration_still_rejects_local_reserved_domain(self):
        with self.assertRaises(ValidationError):
            RegisterIn(
                email="new-user@example.local",
                username="newuser",
                password="Password1!",
                confirm_password="Password1!",
                code="1234",
            )


if __name__ == "__main__":
    unittest.main()
