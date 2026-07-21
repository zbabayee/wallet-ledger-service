from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.wallets.models import Wallet, Currency, WalletStatus


class WalletAPIViewTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="zahra", password="password123",
            email="zahra@test.com", mobile="09130650487"
        )
        self.other_user = User.objects.create_user(
            username="other", password="password123",
            email="other@test.com", mobile="09130650480"
        )
        self.currency = Currency.objects.create(code="USD", name="US Dollar")

    def test_create_wallet_success(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("wallet-list")
        response = self.client.post(url, {"currency": self.currency.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Wallet.objects.filter(user=self.user, currency=self.currency).exists()
        )

    def test_create_wallet_requires_authentication(self):
        self.client.force_authenticate(user=None)
        url = reverse("wallet-list")
        response = self.client.post(url, {"currency": self.currency.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_list_own_wallets(self):
        self.client.force_authenticate(user=self.user)

        Wallet.objects.create(user=self.user, currency=self.currency, balance=Decimal("100"))
        url = reverse("wallet-list")
        response = self.client.get(url)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["balance"],
            "100.00000000"
        )

    def test_user_cannot_see_other_users_wallets(self):
        self.client.force_authenticate(user=self.user)

        Wallet.objects.create(user=self.other_user, currency=self.currency, balance=Decimal("500"))
        url = reverse("wallet-list")
        response = self.client.get(url)
        print(response.data)
        results = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(results), 0)

    def test_multiple_wallets_for_same_user_allowed(self):
        Wallet.objects.all().delete()
        eur = Currency.objects.create(code="EUR", name="Euro")
        Wallet.objects.create(user=self.user, currency=self.currency, balance=Decimal("100"))
        Wallet.objects.create(user=self.user, currency=eur, balance=Decimal("200"))
        wallets = Wallet.objects.filter(user=self.user)
        self.assertEqual(wallets.count(), 2)