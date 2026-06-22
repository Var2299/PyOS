from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Node

User = get_user_model()


class FilesystemTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pass1234")
        resp = self.client.post(
            "/api/auth/login/", {"username": "alice", "password": "pass1234"}
        )
        self.token = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def _create(self, name, node_type=Node.DIRECTORY, parent=None, content=""):
        return self.client.post(
            "/api/nodes/",
            {"name": name, "node_type": node_type, "parent": parent, "content": content},
            format="json",
        )

    def test_create_directory(self):
        resp = self._create("docs")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["path"], "/docs")

    def test_create_file_in_directory(self):
        d = self._create("docs").data
        resp = self._create("a.txt", Node.FILE, parent=d["id"], content="hello")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["path"], "/docs/a.txt")
        self.assertEqual(resp.data["content"], "hello")

    def test_soft_delete_and_recycle_bin(self):
        d = self._create("trashme").data
        self.client.delete(f"/api/nodes/{d['id']}/")
        bin_resp = self.client.get("/api/nodes/recycle_bin/")
        self.assertEqual(len(bin_resp.data), 1)
        # active listing should not show it
        list_resp = self.client.get("/api/nodes/")
        self.assertEqual(len(list_resp.data), 0)

    def test_restore(self):
        d = self._create("keepme").data
        self.client.delete(f"/api/nodes/{d['id']}/")
        self.client.post(f"/api/nodes/{d['id']}/restore/")
        list_resp = self.client.get("/api/nodes/")
        self.assertEqual(len(list_resp.data), 1)

    def test_recursive_soft_delete(self):
        parent = self._create("parent").data
        child = self._create("child.txt", Node.FILE, parent=parent["id"]).data
        self.client.delete(f"/api/nodes/{parent['id']}/")
        self.assertTrue(Node.objects.get(id=child["id"]).is_deleted)

    def test_search(self):
        self._create("report.txt", Node.FILE, content="quarterly numbers")
        resp = self.client.get("/api/nodes/search/?q=quarterly")
        self.assertEqual(len(resp.data), 1)


class AuthTests(APITestCase):
    def test_register_and_login(self):
        resp = self.client.post(
            "/api/auth/register/",
            {"username": "newuser", "email": "n@e.com", "password": "secret123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        login = self.client.post(
            "/api/auth/login/", {"username": "newuser", "password": "secret123"}
        )
        self.assertIn("access", login.data)

    def test_first_user_becomes_admin(self):
        resp = self.client.post(
            "/api/auth/register/",
            {"username": "founder", "email": "f@e.com", "password": "secret123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["is_admin_role"])
        founder = User.objects.get(username="founder")
        self.assertTrue(founder.is_admin_role)
        self.assertTrue(founder.is_staff)

    def test_second_user_is_regular(self):
        self.client.post(
            "/api/auth/register/",
            {"username": "founder", "password": "secret123"},
            format="json",
        )
        resp = self.client.post(
            "/api/auth/register/",
            {"username": "member", "password": "secret123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertFalse(resp.data["is_admin_role"])
        member = User.objects.get(username="member")
        self.assertFalse(member.is_admin_role)
        self.assertFalse(member.is_staff)

    def test_protected_endpoint_requires_auth(self):
        resp = self.client.get("/api/nodes/")
        self.assertEqual(resp.status_code, 401)


class AccessControlTests(APITestCase):
    """Tests for admin sudo override and shared (read-only/public) nodes."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pass1234")
        self.bob = User.objects.create_user(username="bob", password="pass1234")
        self.admin = User.objects.create_user(
            username="root", password="pass1234", is_admin_role=True
        )

    def _auth(self, username):
        r = self.client.post("/api/auth/login/", {"username": username, "password": "pass1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def _make(self, name, perm=Node.PRIVATE, ntype=Node.FILE, content="secret"):
        return self.client.post(
            "/api/nodes/",
            {"name": name, "node_type": ntype, "parent": None,
             "content": content, "permission_level": perm},
            format="json",
        )

    def test_private_node_hidden_from_others(self):
        self._auth("alice")
        self._make("private.txt", Node.PRIVATE)
        self._auth("bob")
        resp = self.client.get("/api/nodes/")
        self.assertEqual(len(resp.data), 0)

    def test_readonly_node_visible_but_not_editable(self):
        self._auth("alice")
        node = self._make("shared.txt", Node.READ_ONLY).data
        self._auth("bob")
        # visible
        resp = self.client.get("/api/nodes/")
        self.assertEqual(len(resp.data), 1)
        self.assertFalse(resp.data[0]["can_edit"])
        # not editable
        edit = self.client.patch(f"/api/nodes/{node['id']}/", {"content": "hacked"}, format="json")
        self.assertEqual(edit.status_code, 403)
        # not deletable
        delete = self.client.delete(f"/api/nodes/{node['id']}/")
        self.assertEqual(delete.status_code, 403)

    def test_public_node_editable_by_others(self):
        self._auth("alice")
        node = self._make("public.txt", Node.PUBLIC).data
        self._auth("bob")
        edit = self.client.patch(f"/api/nodes/{node['id']}/", {"content": "edited"}, format="json")
        self.assertEqual(edit.status_code, 200)
        # but bob cannot delete a public node he doesn't own
        delete = self.client.delete(f"/api/nodes/{node['id']}/")
        self.assertEqual(delete.status_code, 403)

    def test_non_owner_cannot_change_permission(self):
        self._auth("alice")
        node = self._make("public.txt", Node.PUBLIC).data
        self._auth("bob")
        resp = self.client.patch(
            f"/api/nodes/{node['id']}/", {"permission_level": "private"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)
