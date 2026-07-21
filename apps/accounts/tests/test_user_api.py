import pytest

from django.urls import reverse


@pytest.mark.django_db
class TestUserAPI:


    def test_user_list(
        self,
        api_client,
        user,
    ):
        api_client.force_authenticate(user=user)
        response = api_client.get(
            reverse("user-list")
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1


    def test_admin_can_see_inactive_users(
        self,
        api_client,
        admin_user,
        user,
    ):
        user.is_active = False
        user.save()
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(
            reverse("user-list")
        )
        assert response.status_code == 200
        usernames = [
            item["username"]
            for item in response.data["results"]
        ]
        assert user.username in usernames



    def test_search_users(
        self,
        api_client,
        user,
    ):

        api_client.force_authenticate(user=user)
        response = api_client.get(
            reverse("user-list"),
            {
                "search": "zahra"
            }
        )
        assert response.status_code == 200
        assert response.data["results"][0]["username"] == "zahra"


    def test_filter_active_users(
        self,
        api_client,
        admin_user,
        user,
    ):

        user.is_active = False
        user.save()
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(
            reverse("user-list"),
            {
                "is_active": False
            }
        )
        assert response.status_code == 200
        assert response.data["results"][0]["username"] == user.username