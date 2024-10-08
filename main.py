import datetime  
import json  
import logging  
import os  
import random  
import time  
import requests  

# Configure logging  
logging.basicConfig(level=logging.INFO)  

URL = "https://api.divar.ir/v8/web-search/{SEARCH_CONDITIONS}".format(**os.environ)  
BOT_TOKEN = "{BOT_TOKEN}".format(**os.environ)  
BOT_CHATID = "{BOT_CHATID}".format(**os.environ)  

proxy_config = {}  
if os.environ.get("HTTP_PROXY", ""):  
    proxy_config["HTTP_PROXY"] = os.environ.get("HTTP_PROXY")  
if os.environ.get("HTTPS_PROXY", ""):  
    proxy_config["HTTPS_PROXY"] = os.environ.get("HTTPS_PROXY")  

TOKENS = list()  

def get_data(page=None):  
    api_url = URL  
    if page:  
        api_url += f"&page={page}"  
    response = requests.get(api_url)  
    logging.info("Fetched data from API: %s", response.status_code)  
    return response  

def parse_data(data):  
    return json.loads(data.text)  

def get_houses_list(data):  
    logging.info("Checking for houses list in data...")  
    if "web_widgets" in data:  
        return data["web_widgets"].get("post_list", [])  
    if "jli" in data:  
        # Consider extracting information from the 'jli' key if applicable  
        logging.warning("'web_widgets' not found, checking 'jli'...")  
        # Define logic to extract data from 'jli' as required  
        return extract_from_jli(data["jli"])  
    logging.error("Neither 'web_widgets' nor 'jli' were found in data.")  
    return []

def extract_house_data(house):  
    data = house["data"]  
    return {  
        "title": data["title"],  
        "description": f'{data["top_description_text"]} \n {data["middle_description_text"]}',  
        "district": data["action"]["payload"]["web_info"]["district_persian"],  
        "hasImage": data["image_count"] > 0,  
        "token": data["token"],  
    }  

def send_telegram_message(house):  
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"  
    text = f"<b>{house['title']}</b>" + "\n"  
    text += f"<i>{house['district']}</i>" + "\n"  
    text += f"{house['description']}" + "\n"  
    text += f'<i>تصویر : </i> {"✅" if house["hasImage"] else "❌"}\n\n'  
    text += f"https://divar.ir/v/a/{house['token']}"  
    body = {"chat_id": BOT_CHATID, "parse_mode": "HTML", "text": text}  
    result = requests.post(url, data=body, proxies=proxy_config)  
    if result.status_code == 429:  
        logging.warning("Rate limit hit. Retrying...")  
        time.sleep(random.randint(3, 7))  
        send_telegram_message(house)  

def load_tokens():  
    token_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "tokens.json")  
    with open(token_path, "r") as content:  
        if content == "":  
            return []  
        return json.load(content)  

def save_tokns(tokens):  
    token_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "tokens.json")  
    with open(token_path, "w") as outfile:  
        json.dump(tokens, outfile)  

def get_data_page(page=None):  
    data = get_data(page)  
    data = parse_data(data)  
    data = get_houses_list(data)  
    logging.info("Data retrieved from get_houses_list: %s", data)  # Log the fetched houses list  
    data = data[::-1]  
    return data  

def process_data(data, tokens):  
    for house in data:  
        house_data = extract_house_data(house)  
        if house_data is None:  
            logging.warning("No house data extracted, skipping. House: %s", house)  
            continue  
        if house_data["token"] in tokens:  
            logging.info("Duplicate token found, skipping house: %s", house_data["token"])  
            continue  

        tokens.append(house_data["token"])  
        logging.info("Sending message for house: %s", house_data["title"])  
        send_telegram_message(house_data)  
        time.sleep(1)  
    return tokens  

if __name__ == "__main__":  
    logging.info(datetime.datetime.now())  
    tokens = load_tokens()  
    logging.info("Loaded tokens count: %d", len(tokens))  
    pages = [2, ""]  
    for page in pages:  
        logging.info("Processing page: %s", page)  
        data = get_data_page(page)  
        tokens = process_data(data, tokens)  
    
    save_tokns(tokens)  
    logging.info("Tokens saved successfully.")
