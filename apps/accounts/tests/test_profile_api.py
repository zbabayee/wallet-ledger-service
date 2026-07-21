import pytest

from django.urls import reverse


@pytest.mark.django_db
class TestProfileAPI:

    def test_get_user_detail(
            self,
            api_client,
            user,
    ):
        api_client.force_authenticate(user=user)
        response = api_client.get(
            reverse(
                "user-detail",
                kwargs={
                    "pk": user.id
                }
            )
        )
        assert response.status_code == 200
        assert response.data["username"] == user.username

    def test_update_user_profile(
            self,
            api_client,
            user,
    ):
        api_client.force_authenticate(user=user)
        response = api_client.patch(
            reverse(
                "user-detail",
                kwargs={
                    "pk": user.id
                }
            ),
            {
                "first_name": "Zahra"
            },
            format="json",
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.first_name == "Zahra"

    def test_soft_delete_user(
            self,
            api_client,
            user,
    ):
        api_client.force_authenticate(user=user)
        response = api_client.delete(
            reverse(
                "user-detail",
                kwargs={
                    "pk": user.id
                }
            )
        )

        assert response.status_code == 204
        user.refresh_from_db()
        assert user.is_active is False

    def test_get_current_user(
            self,
            api_client,
            user,
    ):
        api_client.force_authenticate(user=user)
        response = api_client.get(
            reverse("user-me")
        )
        assert response.status_code == 200
        assert response.data["username"] == user.username

    def test_update_current_user(
            self,
            api_client,
            user,
    ):
        api_client.force_authenticate(user=user)
        response = api_client.patch(
            reverse("user-me"),
            {
                "first_name": "Z"
            },
            format="json",
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.first_name == "Z"
