# python
import logging
import requests
import argparse
import getpass
from tqdm import tqdm
from title_annotator.base_objects import ChunkImport, RatingRequestNew
from tools.common import chunk_to_rating_request

logging.basicConfig(level=logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Load JSONL file with chunks, transform each to RatingRequestNew and send it to appliction API.")
    parser.add_argument("--input-file", "-i", type=str, required=True,
                        help="Path to the input JSONL file containing chunks.")
    parser.add_argument("--api-endpoint", "-a", type=str, required=True,
                        help="API endpoint to send the rating requests to.")
    parser.add_argument("--username", "-u", type=str, required=False,
                        help="Username for login to the API.")
    parser.add_argument("--password", "-p", type=str, required=False,
                        help="Password for login to the API. If omitted and username provided, will prompt.")
    return parser.parse_args()


def create_api_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json'
    })
    return session


def login(session: requests.Session, api_endpoint: str, username: str, password: str):
    url = f"{api_endpoint}/auth/jwt/login"
    data = {
        "grant_type": "password",
        "username": username,
        "password": password
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    resp = session.post(url, data=data, headers=headers)
    if resp.status_code  != 200:
        logging.error(f"Login failed: {resp.status_code} {resp.text}")
        raise Exception(f"Login failed: {resp.status_code} {resp.text}")
    token_response = resp.json()
    access_token = token_response.get("access_token")
    token_type = token_response.get("token_type", "Bearer")
    if not access_token:
        logging.error("Login response did not contain access_token.")
        raise Exception("Login response did not contain access_token.")
    session.headers.update({"Authorization": f"{token_type} {access_token}"})
    logging.info("Login successful, Authorization header set.")


def send_rating_request(session: requests.Session, api_endpoint: str, rating_request: RatingRequestNew):
    url = f"{api_endpoint}/api/rating/request"
    response = session.post(url, json=rating_request.model_dump())
    if response.status_code != 201:
        logging.error(f"Failed to send rating request {rating_request.id}: {response.status_code} {response.text}")
        raise Exception(f"Failed to send rating request {rating_request.id}: {response.status_code} {response.text}")
    logging.info(f"Successfully sent rating request {rating_request.id}")


def main():
    args = parse_args()
    session = create_api_session()

    if args.username:
        pwd = args.password or getpass.getpass(prompt="Password: ")
        login(session, args.api_endpoint.rstrip("/"), args.username, pwd)

    with open(args.input_file, 'r', encoding='utf-8') as f:
        for line in tqdm(f, desc="Processing chunks"):
            line = line.strip()
            if not line:
                continue
            chunk = ChunkImport.model_validate_json(line)
            rating_request = chunk_to_rating_request(chunk)
            send_rating_request(session, args.api_endpoint.rstrip("/"), rating_request)
    logging.info("All rating requests have been sent.")


if __name__ == "__main__":
    main()