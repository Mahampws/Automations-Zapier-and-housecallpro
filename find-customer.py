import requests

# IMPORTANT:
# Replace this with a newly generated API key.
API_KEY = input_data.get("api_key") or "YOUR_NEW_API_KEY"

# Map the webhook invoice ID to an input field named "invoice_id"
INVOICE_ID = str(input_data.get("invoice_id") or "").strip()

BASE_URL = "https://api.housecallpro.com"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

output = {}


def api_get(endpoint, params=None):
    """Make a GET request to Housecall Pro and return JSON."""
    response = requests.get(
        f"{BASE_URL}{endpoint}",
        headers=HEADERS,
        params=params,
        timeout=20
    )

    if response.status_code != 200:
        raise Exception(
            f"Housecall Pro request failed for {endpoint}: "
            f"{response.status_code} {response.text}"
        )

    return response.json()


def unwrap_record(data, possible_keys):
    """Handle both wrapped and unwrapped API responses."""
    if not isinstance(data, dict):
        return {}

    for key in possible_keys:
        value = data.get(key)
        if isinstance(value, dict):
            return value

    return data


try:
    if not INVOICE_ID:
        raise Exception(
            "No invoice ID was received. Map the webhook invoice ID "
            "to the Code step input field named 'invoice_id'."
        )

    # ---------------------------------------------------------
    # Step 1: Find the invoice and get its job_id
    # ---------------------------------------------------------
    matched_invoice = None
    page = 1
    page_size = 100

    while True:
        invoice_response = api_get(
            "/invoices",
            params={
                "page": page,
                "page_size": page_size
            }
        )

        invoices = (
            invoice_response.get("invoices")
            or invoice_response.get("data")
            or []
        )

        for invoice in invoices:
            api_invoice_id = str(invoice.get("id") or "").strip()
            invoice_number = str(
                invoice.get("invoice_number") or ""
            ).strip()

            # This allows either the internal invoice UUID
            # or the visible invoice number to be supplied.
            if INVOICE_ID in (api_invoice_id, invoice_number):
                matched_invoice = invoice
                break

        if matched_invoice:
            break

        total_pages = invoice_response.get("total_pages")

        if total_pages is not None:
            try:
                if page >= int(total_pages):
                    break
            except (TypeError, ValueError):
                pass

        # Stop when the API returns fewer than one full page.
        if len(invoices) < page_size:
            break

        page += 1

    if not matched_invoice:
        raise Exception(
            f"No invoice was found with ID or invoice number: {INVOICE_ID}"
        )

    job_id = str(matched_invoice.get("job_id") or "").strip()

    if not job_id:
        raise Exception(
            f"Invoice {INVOICE_ID} was found, but it did not contain a job_id."
        )

    # ---------------------------------------------------------
    # Step 2: Retrieve the job
    # ---------------------------------------------------------
    job_response = api_get(f"/jobs/{job_id}")
    job = unwrap_record(job_response, ["job", "data"])

    customer = job.get("customer") or {}
    customer_id = str(
        customer.get("id")
        or job.get("customer_id")
        or ""
    ).strip()

    # ---------------------------------------------------------
    # Step 3: Retrieve the full customer when needed
    # ---------------------------------------------------------
    customer_email = str(customer.get("email") or "").strip().lower()

    if customer_id and not customer_email:
        customer_response = api_get(f"/customers/{customer_id}")
        customer = unwrap_record(
            customer_response,
            ["customer", "data"]
        )

        customer_email = str(
            customer.get("email") or ""
        ).strip().lower()

    # Optional fallback: look inside customer contacts.
    if not customer_email:
        for contact in customer.get("contacts") or []:
            contact_email = str(
                contact.get("email") or ""
            ).strip().lower()

            if contact_email:
                customer_email = contact_email
                break

    if not customer_email:
        raise Exception(
            f"Customer {customer_id or 'unknown'} was found, "
            "but no email address is saved for that customer."
        )

    # ---------------------------------------------------------
    # Final output for the next automation step
    # ---------------------------------------------------------
    output = {
        "invoice_id": matched_invoice.get("id"),
        "invoice_number": matched_invoice.get("invoice_number"),
        "job_id": job_id,
        "customer_id": customer_id,
        "customer_email": customer_email,
        "customer_first_name": customer.get("first_name"),
        "customer_last_name": customer.get("last_name"),
        "customer": customer
    }

except requests.RequestException as error:
    output = {
        "error": f"Network request failed: {str(error)}"
    }

except Exception as error:
    output = {
        "error": str(error)
    }
