import os
import json
import questionary
from loguru import logger
from dotenv import load_dotenv

README_URL = "https://github.com/nir007/odos_swap_api/blob/master/Readme.md"

def is_number(val: str) -> bool:
    return val.replace(".", "").isdigit()

def get_start_up_settings():
    load_dotenv()

    try:
        proxy = os.getenv("PROXY")
        private = os.getenv("PRIVATE")
        base_url = os.getenv("BASE_URL")

        if not private:
            raise RuntimeError(f"Setup your private key in .env file please. \nSee {README_URL}")

        if not base_url:
            raise RuntimeError(f"Setup ODOS api base url in .env file please. \nSee {README_URL}")

        return proxy, private, base_url

    except Exception as e:
        logger.error(f"Invalid startup data: {e}")

def get_user_input_params():
    with open("chains.json", "r") as file:
        chains: dict = json.load(file)

    chain_name = ""
    while not chain_name in chains.keys():
        chain_name = input(f"Enter chain name {list(chains.keys())}: ")

    chain_tokens = dict(chains.get(chain_name).get("tokens")).keys()

    token_from = ""
    while not token_from in chain_tokens:
        token_from = input(f"Enter token from {list(chain_tokens)}: ")

    token_to = ""
    while not token_to in chain_tokens or token_from == token_to:
        token_to = input(f"Enter token to {list(chain_tokens)}: ")

        if token_from == token_to:
            logger.warning("Choose different tokens for swapping please!")

    amount = 0
    while not amount:
        amount = input(f"Enter {token_from.upper()} amount: ")

        if not is_number(amount):
            logger.warning("Enter number please!")
            amount = 0

    slippage = 0
    while not slippage:
        slippage = input(f"Enter swap slippage in percents: ")

        if not is_number(slippage):
            logger.warning("Enter number please!")
            slippage = 0

    return chains.get("chain_name"), amount, slippage, token_from, token_to