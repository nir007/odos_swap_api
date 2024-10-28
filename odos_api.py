import http.client
from aiohttp import ClientSession
from exections import GetQuoteError, AssembleError
from w3_client import W3Client


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
            json=data,
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

    async def __get_quote(self, *, amount: float, slippage: float, token_name_from, token_name_to):
        token_address_from = self._chain.get(token_name_from).get("contract")
        token_decimals_from = self._chain.get(token_name_from).get("decimals")
        token_address_to = self._chain.get(token_name_to).get("contract")

        payload = {
            "chainId":  await self.w3.eth.chain_id,
            "compact": True,
            #"gasPrice": await self.w3.eth.gas_price,
            "userAddr": self._address,
            "slippageLimitPercent": slippage,
            "inputTokens": [{
                "tokenAddress": token_address_from,
                "amount": str(self.to_wei(amount=amount, decimals=token_decimals_from))
            }],
            "outputTokens": [{
                "tokenAddress": token_address_to,
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

    async def asemble(self, *, amount: float, slippage: float, token_name_from, token_name_to):
        quite = await self.__get_quote(
            amount=amount,
            slippage=slippage,
            token_name_from=token_name_from,
            token_name_to=token_name_to,
        )

        payload = {
            "pathId":  quite.get("pathId"),
            "simulate": True,
            "userAddr": self._address
        }

        content = await self.__send_request(
            method="POST",
            url=f"{self.__base_url}{self.__assemble_path}",
            data=payload
        )

        print(content)

        if "simulation" in content:
            simulation = content.get("simulation")
            is_success = simulation.get("isSuccess")

            if not is_success and "simulationError" in simulation:
                raise AssembleError(simulation["simulationError"].get("errorMessage"))

        if "transaction" not in content:
            raise AssembleError("Can`t find transaction info in response")

        trx_data = content.get("transaction")
        value = trx_data.get("value")
        contract_to = trx_data.get("to")
        call_data = trx_data.get("data")

        return content

    async def make_transaction(self):
        pass