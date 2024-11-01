import http.client
from aiohttp import ClientSession
from exections import GetQuoteError, AssembleError
from w3_client import W3Client
from colorama import Fore, Style

class OdosAPI(W3Client):
    def __init__(self, *, session: ClientSession, private, base_url, quote_path, assemble_path, proxy, chain: dict):
        super().__init__(
            proxy=proxy,
            private=private,
            chain=chain
        )

        self.__session = session
        self.__base_url = base_url
        self.__quote_path = quote_path
        self.__assemble_path = assemble_path

    async def __send_request(self, *, url: str, method: str = "GET", data: {}):
        print(f"Sent request to {method}: {url}")

        async with self.__session.request(
            method=method,
            url=url,
            json=data if method != "GET" else None,
            params=data if method == "GET" else None,
            timeout=10,
            allow_redirects=False,
            headers={
                "Content-Type": "application/json"
            }
        ) as res:
            content = await res.json(content_type=res.headers["Content-Type"])

            if res.status not in (http.client.OK, http.client.CREATED, http.client.NO_CONTENT):
                raise RuntimeError(f"Bad response code from {url}: {res.status} {content}")

            return content

    async def __get_swap_data(self, *, amount: float, slippage: float, token_name_from, token_name_to) -> dict:
        token_address_from = self._chain.get(token_name_from).get("contract")
        token_decimals_from = self._chain.get(token_name_from).get("decimals")
        token_address_to = self._chain.get(token_name_to).get("contract")

        payload = {
            "chainId":  await self._w3.eth.chain_id,
            "compact": True,
            #"gasPrice": await self.w3.eth.gas_price,
            "userAddr": self._account_address,
            "slippageLimitPercent": slippage,
            "inputTokens": [{
                "tokenAddress": self._w3.to_checksum_address(token_address_from),
                "amount": str(self._to_wei(amount=amount, decimals=token_decimals_from))
            }],
            "outputTokens": [{
                "tokenAddress": self._w3.to_checksum_address(token_address_to),
                "proportion": 1
            }]
        }

        content = await self.__send_request(
            method="POST",
            url=f"{self.__base_url}{self.__quote_path}",
            data=payload
        )

        if "pathId" not in content:
            raise GetQuoteError("Can`t get pathId")

        return content

    async def __asemble(self, *, quite):
        payload = {
            "pathId":  quite.get("pathId"),
            "simulate": False,
            "userAddr": self._account_address
        }

        content = await self.__send_request(
            method="POST",
            url=f"{self.__base_url}{self.__assemble_path}",
            data=payload
        )

        if "simulation" in content and content.get("simulation") is not None:
            simulation = content.get("simulation")
            is_success = simulation.get("isSuccess")

            if not is_success and "simulationError" in simulation:
                raise AssembleError(simulation["simulationError"].get("errorMessage"))

        if "transaction" not in content:
            raise AssembleError("Can`t find transaction info in response")

        return content

    async def swap(self, *, amount: float, slippage: float, token_name_from, token_name_to):
        native_balance = await self._get_native_balance()

        print(Fore.GREEN + f"Native token balance: {native_balance:.5f}")
        print(Style.RESET_ALL)

        quite = await self.__get_swap_data(
            amount=amount,
            slippage=slippage,
            token_name_from=token_name_from,
            token_name_to=token_name_to,
        )

        if not self._is_native_token(token_name_from):
            decimals = self._chain.get(token_name_from).get("decimals")
            tx_hash = await self._approve(token_name_from, self._to_wei(amount=amount, decimals=decimals))
            print(f"Approve transaction sent: {tx_hash.hex()}")

            await self._wait_tx(hex_bytes=tx_hash)

        assembled_transaction = await self.__asemble(quite=quite)

        transaction = assembled_transaction.get("transaction")
        transaction["value"] = int(transaction["value"])

        tx_hash = await self._send_transaction(transaction)
        print(f"Transaction sent: {tx_hash.hex()}")

        await self._wait_tx(hex_bytes=tx_hash)
