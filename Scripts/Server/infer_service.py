import requests

from config import Config


def infer_image(image_url):
    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Token': Config.INFER_AK
    }

    payload = {
        "image_url": image_url
    }

    response = requests.post(Config.INFER_URL, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to perform inference: {response.text}")
