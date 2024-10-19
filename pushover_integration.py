import requests
import configparser


def load_pushover_config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return {
        "user_key": config["Pushover"]["user_key"],
        "api_token": config["Pushover"]["api_token"],
    }


def send_pushover_notification(title, message, config):
    url = "https://api.pushover.net/1/messages.json"
    data = {
        "token": config["api_token"],
        "user": config["user_key"],
        "title": title,
        "message": message,
    }
    response = requests.post(url, data=data)
    print(response.text)
    print(response.status_code)
    return response.status_code == 200
