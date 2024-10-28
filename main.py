import os
import asyncio
import sys
import json
from dotenv import load_dotenv
from aiohttp_socks import ProxyConnector
from aiohttp import ClientSession, TCPConnector
from colorama import Fore, Style

from exections import GetQuoteError, AssembleError
from odos_api import OdosAPI
from web3.exceptions import Web3RPCError

async def main():
    load_dotenv()

    proxy = os.getenv("PROXY")
    private = os.getenv("PRIVATE")
    base_url = os.getenv("BASE_URL")
    quote_path = os.getenv("QUOTE_PATH")
    assemble_path = os.getenv("ASSEMBLE")

    session = ClientSession(
        connector=ProxyConnector.from_url(f"http://{proxy}") if proxy else TCPConnector(),
    )

    try:
        with open("chains.json", "r") as file:
            chains: dict = json.load(file)

        api = OdosAPI(
            session=session,
            base_url=base_url,
            quote_path=quote_path,
            assemble_path=assemble_path,
            proxy=proxy,
            private=private,
            chain=chains.get("scroll")
        )

        tx_hash = await api.swap(
            amount=0.1,
            slippage=0.4,
            token_name_from="usdt",
            token_name_to="usdc"
        )

        print(tx_hash)

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
        print(Style.RESET_ALL)
        await session.close()

asyncio.run(main())





