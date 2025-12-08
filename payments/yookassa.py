#payments/yookassa.py
import httpx
from config import YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY

async def create_payment(
    amount: str,
    description: str,
    customer: dict,
    return_url: str,
    metadata: dict
) -> tuple[dict, int]:
    # Нормализуем сумму к формату X.XX
    amount_value = "{:.2f}".format(float(amount))
    payload = {
        "amount": {"value": amount_value, "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": description,
        "metadata": metadata,
        "receipt": {
            "customer": customer,
            "items": [
                {
                    "description": description,
                    "amount": {"value": amount_value, "currency": "RUB"},
                    "quantity": 1,
                    "vat_code": 1,
                    "payment_subject": "service",
                    "payment_mode": "full_payment"
                }
            ]
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.yookassa.ru/v3/payments",  # ← УБРАТЬ ПРОБЕЛЫ!
            json=payload,
            auth=(YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY),
            headers={"Idempotence-Key": f"vip_{metadata['user_id']}_{int(__import__('time').time())}"}
        )
        return response.json(), response.status_code
    
async def check_payment(payment_id: str) -> tuple[dict, int]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.yookassa.ru/v3/payments/{payment_id}",
            auth=(YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY)
        )
        return response.json(), response.status_code