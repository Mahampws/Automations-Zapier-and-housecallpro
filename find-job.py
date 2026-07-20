import requests
import copy

API_KEY = "xxxxxxxxxxxxxxxxxxxxxxx"
CUSTOMER_ID = input_data.get("customer_id")

BASE = "https://api.housecallpro.com"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

output = {}

# Get all jobs for the customer
resp = requests.get(
    f"{BASE}/jobs",
    headers=HEADERS,
    params={"customer_id": CUSTOMER_ID, "page_size": 50},
    timeout=15
)

if resp.status_code != 200:
    output["error"] = f"Job fetch failed: {resp.status_code} {resp.text}"
else:
    data = resp.json()
    jobs = data.get("jobs") or data.get("data") or []

    enriched_jobs = []

    for job in jobs:
        # 🔹 Make a full copy of the original job object
        job_full = copy.deepcopy(job)

        # 🔹 Extract SKU from description (if present)
        description = job.get("description", "")
        sku = ""
        if "|" in description:
            sku = description.split("|")[-1].strip()

        # 🔹 Extract job tag names
        tags = job.get("tags", [])
        tag_names = [tag.get("name") for tag in tags if isinstance(tag, dict)]

        # 🔹 Add new fields WITHOUT removing anything
        job_full["product_sku"] = sku
        job_full["job_tags"] = tag_names

        enriched_jobs.append(job_full)

    output = {
        "customer_id": CUSTOMER_ID,
        "jobs": enriched_jobs
    }

print(output)
