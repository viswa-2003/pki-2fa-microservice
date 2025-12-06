import json
import requests

API_URL = "https://eajeyq4r3zljoq4rpovy2nthda0vtjqf.lambda-url.ap-south-1.on.aws"

def request_seed(student_id: str, github_repo_url: str, api_url: str = API_URL):
    """
    Request encrypted seed from instructor API and save to encrypted_seed.txt
    """
    # 1. Read student public key from PEM file
    with open("student_public.pem", "r") as f:
        public_key_pem = f.read()

    # 2. Prepare HTTP POST payload
    payload = {
        "student_id": student_id,
        "github_repo_url": github_repo_url,
        "public_key": public_key_pem
    }

    # 3. Send POST request
    try:
        resp = requests.post(
            api_url,
            json=payload,
            timeout=15,
            headers={"Content-Type": "application/json"},
        )
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return

    # 4. Parse JSON response
    try:
        data = resp.json()
    except json.JSONDecodeError:
        print("Invalid JSON response:", resp.text)
        return

    if resp.status_code != 200 or data.get("status") != "success":
        print("API error:", data)
        return

    encrypted_seed = data.get("encrypted_seed")
    if not encrypted_seed:
        print("Missing 'encrypted_seed' in response:", data)
        return

    # 5. Save encrypted seed to file
    with open("encrypted_seed.txt", "w") as f:
        f.write(encrypted_seed.strip())

    print("✅ Encrypted seed saved to encrypted_seed.txt")

if __name__ == "__main__":
    STUDENT_ID = "22P31A42C4"
    GITHUB_REPO_URL = "https://github.com/viswa-2003/pki-2fa-microservice"
    request_seed(STUDENT_ID, GITHUB_REPO_URL)
