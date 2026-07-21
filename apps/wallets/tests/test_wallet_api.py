from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from wallets.models import Wallet, Currency


class WalletAPIViewTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="zahra",
            password="password123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="password123",
        )
        self.currency = Currency.objects.create(code="USD",name="US Dollar")
        self.client.force_authenticate(user=self.user)

    def test_create_wallet_success(self):
        url = reverse("wallet-create")
        response = self.client.post(
            url,
            {
                "currency": self.currency.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code,status.HTTP_201_CREATED)
        self.assertTrue(Wallet.objects.filter(
                user=self.user,
                currency=self.currency,
            ).exists()
        )


    def test_create_wallet_requires_authentication(self):
        self.client.force_authenticate(user=None)

        url = reverse("wallet-create")
        response = self.client.post(
            url,
            {
                "currency": self.currency.id,
            },
            format="json",)
        self.assertEqual(response.status_code,status.HTTP_401_UNAUTHORIZED)


    def test_user_can_list_own_wallets(self):
        Wallet.objects.create(
            user=self.user,
            currency=self.currency,
            balance=Decimal("100")
        )
        url = reverse("wallet-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data),1)


    def test_user_cannot_see_other_users_wallets(self):
        Wallet.objects.create(
            user=self.other_user,
            currency=self.currency,
            balance=Decimal("500")
        )
        url = reverse(
            "wallet-list"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data),0)


    def test_multiple_wallets_for_same_user_allowed(self):
        Wallet.objects.create(
            user=self.user,
            currency=self.currency,
            balance=Decimal("100")
        )
        Wallet.objects.create(
            user=self.user,
            currency=self.currency,
            balance=Decimal("200")
        )
        wallets = Wallet.objects.filter(
            user=self.user
        )
        self.assertEqual( wallets.count(),2)