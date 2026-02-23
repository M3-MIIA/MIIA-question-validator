import os
import json
import time
import requests
from dotenv import load_dotenv


class MIIA_API:

    def __init__(self):
        self.base_url = os.environ.get("BASE_URL")
        self.token = os.environ.get("MIIA_API_TOKEN")
        if not self.base_url or not self.token:
            raise ValueError("ERROR: BASE_URL or MIIA_API_TOKEN missing from .env.")

    def create_job(self, integration_id, answer):
        url_post = f"{self.base_url}/textual-corrections/v1/discursive/{integration_id}/assess"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        print(f"1. Sending POST to create Job...")
        if isinstance(answer, str):
            answer = json.loads(answer, strict=False)
        try:
            response_post = requests.post(url_post, headers=headers, json=answer)
            response_post.raise_for_status()
            data_post = response_post.json()

            job_id = data_post.get("job_id")
            if not job_id:
                raise ValueError("API did not return a valid job_id.")

            print(f"   [Success] Job created: {job_id}")
            return job_id

        except requests.exceptions.RequestException as e:
            print(f"POST request failed: {e}")
            if e.response is not None:
                print(e.response.text)
            exit(1)


    def check_status(self, job_id):
        url_get = f"{self.base_url}/textual-corrections/v1/jobs/{job_id}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        print(f"\n2. Starting Job status check (Polling)...")

        max_try = 15
        interval_s = 4

        for attempt in range(1, max_try + 1):
            try:
                response_get = requests.get(url_get, headers=headers)
                response_get.raise_for_status()

                data_get = response_get.json()
                current_status = data_get.get("status")

                if current_status == "running":
                    print(f"   [{attempt}/{max_try}] Status: running. Waiting {interval_s}s...")
                    time.sleep(interval_s)
                    continue

                elif current_status == "completed" or current_status == "success":
                    print("\n[Success] Processing completed!")
                    print("-" * 40)
                    print(data_get)
                    print("-" * 40)
                    break

                elif current_status == "failed" or current_status == "error":
                    print(f"\n[Backend Error] Job failed internally: {data_get}")
                    break

                else:
                    print(f"\n[Warning] Unknown status returned: '{current_status}'. Full response: {data_get}")
                    break

            except requests.exceptions.RequestException as e:
                print(f"\nNetwork failure during GET: {e}")
                break
        else:
            print("\n[Timeout] Maximum number of attempts reached. Job took too long.")
