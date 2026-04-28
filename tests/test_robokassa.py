from __future__ import annotations

import json
import unittest
from urllib.parse import parse_qs, unquote, urlparse

from app.payments.robokassa import RobokassaSignatureBuilder


class RobokassaSignatureBuilderTests(unittest.TestCase):
    def test_build_payment_link_contains_signature_and_urls(self) -> None:
        builder = RobokassaSignatureBuilder(
            merchant_login="demo",
            password1="pass1",
            password2="pass2",
            hash_algorithm="md5",
            test_mode=True,
        )

        link = builder.build_payment_link(
            amount_rub=599,
            invoice_id=12,
            description="Подписка Pro",
            shp_params={
                "Shp_plan": "pro",
                "Shp_user": "1",
            },
            receipt={
                "sno": "usn_income",
                "items": [
                    {
                        "name": "Подписка Pro",
                        "quantity": 1,
                        "sum": 599,
                        "payment_method": "full_prepayment",
                        "payment_object": "service",
                        "tax": "none",
                    }
                ],
            },
            result_url="https://example.com/result",
            success_url="https://example.com/success",
            fail_url="https://example.com/fail",
        )

        parsed = urlparse(link.payment_url)
        params = parse_qs(parsed.query)

        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "auth.robokassa.ru")
        self.assertEqual(params["MerchantLogin"], ["demo"])
        self.assertEqual(params["OutSum"], ["599.00"])
        self.assertEqual(params["InvId"], ["12"])
        self.assertEqual(params["IsTest"], ["1"])
        self.assertEqual(params["ResultUrl"], ["https://example.com/result"])
        self.assertEqual(params["SuccessUrl"], ["https://example.com/success"])
        self.assertEqual(params["FailUrl"], ["https://example.com/fail"])
        self.assertEqual(params["Shp_plan"], ["pro"])
        self.assertEqual(params["Shp_user"], ["1"])
        self.assertEqual(params["SignatureValue"], [link.signature_value])
        self.assertIn("Receipt", params)
        self.assertEqual(
            json.loads(unquote(params["Receipt"][0])),
            {
                "sno": "usn_income",
                "items": [
                    {
                        "name": "Подписка Pro",
                        "quantity": 1,
                        "sum": 599,
                        "payment_method": "full_prepayment",
                        "payment_object": "service",
                        "tax": "none",
                    }
                ],
            },
        )

    def test_verify_result_signature_accepts_normalized_amount(self) -> None:
        builder = RobokassaSignatureBuilder(
            merchant_login="demo",
            password1="pass1",
            password2="pass2",
            hash_algorithm="md5",
        )

        signature = builder._sign_for_result(  # noqa: SLF001
            out_sum="599.00",
            invoice_id=12,
            shp_params={
                "Shp_plan": "pro",
                "Shp_user": "1",
            },
        )
        self.assertTrue(
            builder.verify_result_signature(
                out_sum="599.00",
                invoice_id=12,
                signature_value=signature,
                shp_params={
                    "Shp_plan": "pro",
                    "Shp_user": "1",
                },
            )
        )
