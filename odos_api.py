import http.client
from aiohttp import ClientSession
from exections import GetQuoteError, AssembleError
from w3_client import W3Client

class OdosClient(W3Client):
    def __init__(self, *, session: ClientSession, private, base_url, proxy, chain: dict):
        super().__init__(
            proxy=proxy,
            private=private,
            chain=chain
        )

        self.__session = session
        self.__base_url = base_url

    async def __send_request(self, *, url: str, method: str = "GET", data: dict = None):
        print(f"Sent request to {method}: {url}")

        async with self.__session.request(
            method=method,
            url=url,
            json=data if method != "GET" else None,
            params=data if method == "GET" else None,
            timeout=15,
            allow_redirects=False,
            headers={
                "Content-Type": "application/json"
            }
        ) as res:
            content = await res.json(content_type=res.headers["Content-Type"])

            if res.status not in (http.client.OK, http.client.CREATED, http.client.NO_CONTENT):
                raise RuntimeError(f"Bad response code from {url}: {res.status} {content}")

            return content

    async def __get_router_address(self) -> str:
        path = f"/info/router/v2/{await self._get_cain_id()}"

        content = await self.__send_request(
            method="GET",
            url=f"{self.__base_url}{path}"
        )

        if "address" not in content:
            raise RuntimeError("Can`t get router info")

        return content.get("address")

    async def __get_quite(self, *, amount: float, slippage: float, token_name_from, token_name_to) -> dict:
        path = "/sor/quote/v2"

        token_address_from = self._chain.get("tokens").get(token_name_from).get("contract")
        token_decimals_from = self._chain.get("tokens").get(token_name_from).get("decimals")
        token_address_to = self._chain.get("tokens").get(token_name_to).get("contract")

        payload = {
            "chainId":  await self._get_cain_id(),
            "compact": True,
            "userAddr": self._account_address,
            "slippageLimitPercent": slippage,
            "inputTokens": [{
                "tokenAddress": self._to_checksum(token_address_from),
                "amount": str(self._to_wei(amount=amount, decimals=token_decimals_from))
            }],
            "outputTokens": [{
                "tokenAddress": self._to_checksum(token_address_to),
                "proportion": 1
            }]
        }

        content = await self.__send_request(
            method="POST",
            url=f"{self.__base_url}{path}",
            data=payload
        )

        if "pathId" not in content:
            raise GetQuoteError("Can`t get pathId")

        return content

    async def __asemble(self, *, quite: dict):
        path = "/sor/assemble"

        payload = {
            "pathId":  quite.get("pathId"),
            "simulate": True,
            "userAddr": self._account_address
        }

        content = await self.__send_request(
            method="POST",
            url=f"{self.__base_url}{path}",
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

    async def swap(self, *, amount: float, slippage: float, token_name_from: str, token_name_to: str):
        quite = await self.__get_quite(
            amount=amount,
            slippage=slippage,
            token_name_from=token_name_from,
            token_name_to=token_name_to,
        )

        if not self._is_native_token(token_name_from):
            decimals = self._chain.get("tokens").get(token_name_from).get("decimals")

            router_address = await self.__get_router_address()

            tx_hash = await self._approve(
                token_name_from,
                router_address,
                self._to_wei(amount=amount, decimals=decimals)
            )

            print(f"Approve transaction sent: {tx_hash.hex()}")

            await self._wait_tx(hex_bytes=tx_hash)

        assembled_transaction = await self.__asemble(quite=quite)

        transaction = assembled_transaction["transaction"]
        transaction["value"] = int(transaction["value"])

        signed_transaction = await self._sign(transaction)

        tx_hash = await self._send_raw_transaction(signed_transaction)

        print(f"Swap: {amount:.10f} {token_name_from.upper()} to {token_name_to.upper()}")
        print(f"Transaction sent: {tx_hash.hex()}")

        await self._wait_tx(hex_bytes=tx_hash)
