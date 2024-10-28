from web3 import AsyncWeb3, AsyncHTTPProvider

class W3Client:
    def __init__(self, *, proxy, private, chain):
        self._chain = chain

        request_kwargs = {
            "proxy": f"http://{proxy}"
        } if proxy else {}

        self.w3 = AsyncWeb3(
            AsyncHTTPProvider(
                self._chain.get("rpc_url"),
                request_kwargs=request_kwargs
            )
        )
        self._address = self.w3.to_checksum_address(
            self.w3.eth.account.from_key(private).address
        )

    def to_wei(self, *, amount: float, decimals: int):
        unit_name = {
            6: "mwei",
            9: "gwei",
            18: "ether",
        }.get(decimals)

        if not unit_name:
            raise RuntimeError(f"Can`t find unit for decimals: {decimals}")

        return self.w3.to_wei(amount, unit_name)