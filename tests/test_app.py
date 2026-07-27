import os
import tempfile
import unittest

from app import app, init_db


class ZafacAppTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test.db")
        app.config.update(TESTING=True, DATABASE=self.db_path)
        self.client = app.test_client()
        init_db()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Zafac Autospares", response.get_data(as_text=True))

    def test_products_page_loads(self):
        response = self.client.get("/products")
        self.assertEqual(response.status_code, 200)
        self.assertIn("View Products", response.get_data(as_text=True))

    def test_admin_login(self):
        response = self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "ZafacAdmin2026!"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Product Management", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
