from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
from urllib.parse import urlencode


class RobokassaError(RuntimeError):
    """Raised when Robokassa payment generation or verification fails."""


@dataclass(frozen=True, slots=True)
class RobokassaPaymentLink:
    payment_url: str
    signature_value: str
    out_sum: str
    payload: dict[str, str]


class RobokassaSignatureBuilder:
    def __init__(
        self,
        *,
        merchant_login: str,
        password1: str,
        password2: str,
        hash_algorithm: str = "md5",
        test_mode: bool = False,
    ) -> None:
        self._merchant_login = merchant_login
        self._password1 = password1
        self._password2 = password2
        self._hash_algorithm = hash_algorithm
        self._test_mode = test_mode

    @property
    def test_mode(self) -> bool:
        return self._test_mode

    def build_payment_link(
        self,
        *,
        amount_rub: int,
        invoice_id: int,
        description: str,
        shp_params: dict[str, str],
        result_url: str | None = None,
        success_url: str | None = None,
        fail_url: str | None = None,
    ) -> RobokassaPaymentLink:
        out_sum = format_amount_rub(amount_rub)
        signature = self._sign_for_payment(
            out_sum=out_sum,
            invoice_id=invoice_id,
            shp_params=shp_params,
        )
        payload = {
            "MerchantLogin": self._merchant_login,
            "OutSum": out_sum,
            "InvId": str(invoice_id),
            "Description": description,
            "SignatureValue": signature,
            "Encoding": "utf-8",
            "Culture": "ru",
        }
        if self._test_mode:
            payload["IsTest"] = "1"
        if result_url:
            payload["ResultUrl"] = result_url
        if success_url:
            payload["SuccessUrl"] = success_url
        if fail_url:
            payload["FailUrl"] = fail_url

        for key, value in _sorted_shp_items(shp_params):
            payload[key] = value

        return RobokassaPaymentLink(
            payment_url=(
                "https://auth.robokassa.ru/Merchant/Index.aspx?"
                f"{urlencode(payload)}"
            ),
            signature_value=signature,
            out_sum=out_sum,
            payload=dict(payload),
        )

    def verify_result_signature(
        self,
        *,
        out_sum: str,
        invoice_id: int,
        signature_value: str,
        shp_params: dict[str, str],
    ) -> bool:
        expected = self._sign_for_result(
            out_sum=out_sum,
            invoice_id=invoice_id,
            shp_params=shp_params,
        )
        return expected.casefold() == signature_value.casefold()

    def verify_success_signature(
        self,
        *,
        out_sum: str,
        invoice_id: int,
        signature_value: str,
        shp_params: dict[str, str],
    ) -> bool:
        expected = self._sign_for_success(
            out_sum=out_sum,
            invoice_id=invoice_id,
            shp_params=shp_params,
        )
        return expected.casefold() == signature_value.casefold()

    def _sign_for_payment(
        self,
        *,
        out_sum: str,
        invoice_id: int,
        shp_params: dict[str, str],
    ) -> str:
        base = f"{self._merchant_login}:{out_sum}:{invoice_id}:{self._password1}"
        return _sign_with_shp_tail(
            base=base,
            shp_params=shp_params,
            algorithm=self._hash_algorithm,
        )

    def _sign_for_result(
        self,
        *,
        out_sum: str,
        invoice_id: int,
        shp_params: dict[str, str],
    ) -> str:
        base = f"{out_sum}:{invoice_id}:{self._password2}"
        return _sign_with_shp_tail(
            base=base,
            shp_params=shp_params,
            algorithm=self._hash_algorithm,
        )

    def _sign_for_success(
        self,
        *,
        out_sum: str,
        invoice_id: int,
        shp_params: dict[str, str],
    ) -> str:
        base = f"{out_sum}:{invoice_id}:{self._password1}"
        return _sign_with_shp_tail(
            base=base,
            shp_params=shp_params,
            algorithm=self._hash_algorithm,
        )


def format_amount_rub(value: int) -> str:
    return f"{Decimal(value).quantize(Decimal('1.00'))}"


def normalize_out_sum(value: str) -> str:
    try:
        decimal_value = Decimal(value)
    except InvalidOperation as error:
        raise RobokassaError("Invalid OutSum received from Robokassa") from error

    return f"{decimal_value.quantize(Decimal('1.00'))}"


def _sign_with_shp_tail(
    *,
    base: str,
    shp_params: dict[str, str],
    algorithm: str,
) -> str:
    parts = [base]
    for key, value in _sorted_shp_items(shp_params):
        parts.append(f"{key}={value}")
    return _hash_string(":".join(parts), algorithm=algorithm)


def _sorted_shp_items(shp_params: dict[str, str]) -> list[tuple[str, str]]:
    return sorted(
        (
            (key, value)
            for key, value in shp_params.items()
            if key.startswith("Shp_")
        ),
        key=lambda item: item[0],
    )


def _hash_string(value: str, *, algorithm: str) -> str:
    normalized = algorithm.casefold()
    mapping = {
        "md5": "md5",
        "ripemd160": "ripemd160",
        "sha1": "sha1",
        "hs1": "sha1",
        "sha256": "sha256",
        "hs256": "sha256",
        "sha384": "sha384",
        "hs384": "sha384",
        "sha512": "sha512",
        "hs512": "sha512",
    }
    try:
        digest_name = mapping[normalized]
    except KeyError as error:
        raise RobokassaError(f"Unsupported Robokassa hash algorithm: {algorithm}") from error

    try:
        hasher = hashlib.new(digest_name)
    except ValueError as error:
        raise RobokassaError(
            f"Hash algorithm is not available in this runtime: {digest_name}"
        ) from error

    hasher.update(value.encode("utf-8"))
    return hasher.hexdigest()
