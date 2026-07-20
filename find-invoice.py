import requests

# =====================================================
# ZAPIER INPUT DATA
# =====================================================

API_KEY = (input_data.get("api_key") or "").strip()
INVOICE_NUMBER = str(input_data.get("invoice_number") or "").strip()
RAW_JOB_TAGS = str(input_data.get("job_tag") or "").strip()

ALLOWED_TAGS = {"xxx", "DIY", "xxx"}

BASE = "https://api.housecallpro.com"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

output = {}

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def cents_to_usd(value):
    try:
        return round(float(value or 0) / 100, 2)
    except (TypeError, ValueError):
        return 0.00


def quantity_from_hundredths(value):
    try:
        return float(value or 0) / 100
    except (TypeError, ValueError):
        return 0


# =====================================================
# VALIDATE REQUIRED INPUTS
# =====================================================

if not API_KEY:
    output["error"] = "Housecall Pro API key is missing."

elif not INVOICE_NUMBER:
    output["error"] = "Invoice number is missing."

else:
    # =====================================================
    # STEP 0: JOB TAG VALIDATION
    # =====================================================

    job_tags = {
        tag.strip()
        for tag in RAW_JOB_TAGS.split(",")
        if tag.strip()
    }

    matched_tags = job_tags & ALLOWED_TAGS

    # Only enforce validation when tags were provided
    if job_tags and not matched_tags:
        output["exit"] = (
            f"Job tags {sorted(job_tags)} are not allowed. "
            "Required tag: Nationwide, DIY, or Wholesale."
        )

    else:
        # =====================================================
        # STEP 1: GET INVOICE
        # =====================================================

        try:
            response = requests.get(
                f"{BASE}/invoices",
                headers=HEADERS,
                params={
                    "invoice_number": INVOICE_NUMBER,
                    "page_size": 50
                },
                timeout=15
            )

        except requests.RequestException as error:
            output["error"] = f"Invoice request failed: {str(error)}"

        else:
            if response.status_code != 200:
                output["error"] = (
                    f"Invoice fetch failed: "
                    f"{response.status_code} {response.text}"
                )

            else:
                try:
                    invoices_data = response.json()
                except ValueError:
                    invoices_data = {}

                invoices = (
                    invoices_data.get("invoices")
                    or invoices_data.get("data")
                    or []
                )

                invoice = None

                for current_invoice in invoices:
                    if (
                        str(current_invoice.get("invoice_number", "")).strip()
                        == INVOICE_NUMBER
                    ):
                        invoice = current_invoice
                        break

                if not invoice:
                    output["error"] = (
                        f"No invoice found with number {INVOICE_NUMBER}"
                    )

                else:
                    # =====================================================
                    # INVOICE-LEVEL MONEY CONVERSION
                    # =====================================================

                    invoice["amount_usd"] = cents_to_usd(
                        invoice.get("amount")
                    )

                    invoice["subtotal_usd"] = cents_to_usd(
                        invoice.get("subtotal")
                    )

                    invoice["due_amount_usd"] = cents_to_usd(
                        invoice.get("due_amount")
                    )

                    # =====================================================
                    # ITEMS
                    # =====================================================

                    items = invoice.get("items") or []

                    # Number of different invoice lines
                    invoice_item_count = len(items)

                    # Total quantity across all invoice lines
                    total_item_quantity = sum(
                        quantity_from_hundredths(
                            item.get("qty_in_hundredths")
                        )
                        for item in items
                    )

                    # Change 3.0 to 3 when quantity is a whole number
                    if float(total_item_quantity).is_integer():
                        total_item_quantity = int(total_item_quantity)

                    for item in items:
                        item["unit_cost_usd"] = cents_to_usd(
                            item.get("unit_cost")
                        )

                        item["unit_price_usd"] = cents_to_usd(
                            item.get("unit_price")
                        )

                        item["amount_usd"] = cents_to_usd(
                            item.get("amount")
                        )

                        item["quantity"] = quantity_from_hundredths(
                            item.get("qty_in_hundredths")
                        )

                        if float(item["quantity"]).is_integer():
                            item["quantity"] = int(item["quantity"])

                    # =====================================================
                    # DISCOUNTS
                    # =====================================================

                    for discount in invoice.get("discounts") or []:
                        discount["amount_usd"] = cents_to_usd(
                            discount.get("amount")
                        )

                    # =====================================================
                    # PAYMENTS
                    # =====================================================

                    for payment in invoice.get("payments") or []:
                        payment["amount_usd"] = cents_to_usd(
                            payment.get("amount")
                        )

                    # =====================================================
                    # ZAPIER OUTPUT
                    # =====================================================

                    output["invoice"] = invoice
                    output["matched_job_tags"] = sorted(matched_tags)
                    output["invoice_amount_usd"] = invoice["amount_usd"]

                    # Different product/service lines
                    output["invoice_item_count"] = invoice_item_count

                    # Combined quantity of all lines
                    output["total_item_quantity"] = total_item_quantity

print(output)
