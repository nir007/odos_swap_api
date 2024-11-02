import os
import asyncio
import sys
import json
from dotenv import load_dotenv
from aiohttp_socks import ProxyConnector
from aiohttp import ClientSession, TCPConnector
from colorama import Fore
from exections import GetQuoteError, AssembleError
from odos_api import OdosClient
from web3.exceptions import Web3RPCError

README_URL = "https://github.com/nir007/odos_swap_api/blob/master/Readme.md"

async def main():
    load_dotenv()

    try:
        proxy = os.getenv("PROXY")
        private = os.getenv("PRIVATE")
        base_url = os.getenv("BASE_URL")

        if not private:
            raise RuntimeError(f"Setup your private key in .env file please. \nSee {README_URL}")

        if not base_url:
            raise RuntimeError(f"Setup odos api base url in .env file please. \nSee {README_URL}")

        session = ClientSession(
            connector=ProxyConnector.from_url(f"http://{proxy}") if proxy else TCPConnector(),
        )

    except Exception as e:
        print(Fore.RED + f"Invalid input data: {e}")
        sys.exit()

    try:
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
                print("Choose different tokens for swapping please!")

        amount = 0
        while not amount:
            amount = input(f"Enter {token_from.upper()} amount: ")

            if not amount.replace(".", "").isdigit():
                print("Enter number please!")
                amount = 0

        slippage = 0
        while not slippage:
            slippage = input(f"Enter swap slippage in percents: ")

            if not slippage.replace(".", "").isdigit():
                print("Enter number please!")
                slippage = 0

        api = OdosClient(
            session=session,
            base_url=base_url,
            proxy=proxy,
            private=private,
            chain=chains.get(chain_name)
        )

        await api.swap(
            amount=float(amount),
            slippage=float(slippage),
            token_name_from=token_from,
            token_name_to=token_to
        )

    except GetQuoteError as e:
        print(Fore.RED + f"Quote. {e}")
    except AssembleError as e:
        print(Fore.RED + f"Assemble. {e}")
    except Web3RPCError as e:
        print(Fore.RED + f"RPC error: {e}")
    except Exception as e:
        _, _, exc_tb = sys.exc_info()
        print(Fore.RED + f"Something went wrong on line {exc_tb.tb_lineno} {e}")
    finally:
        await session.close()

asyncio.run(main())