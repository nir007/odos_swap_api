from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.types import HexBytes, HexStr
from web3.exceptions import TransactionNotFound
import asyncio

class W3Client:
    def __init__(self, *, proxy, private, chain):
        self._chain = chain
        self._private = private

        request_kwargs = {
            "proxy": f"http://{proxy}"
        } if proxy else {}

        self._w3 = AsyncWeb3(
            AsyncHTTPProvider(
                self._chain.get("rpc_url"),
                request_kwargs=request_kwargs
            )
        )
        self._address = self._w3.to_checksum_address(
            self._w3.eth.account.from_key(private).address
        )

    def to_wei(self, *, amount: float, decimals: int):
        unit_name = {
            6: "mwei",
            9: "gwei",
            18: "ether",
        }.get(decimals)

        if not unit_name:
            raise RuntimeError(f"Can`t find unit for decimals: {decimals}")

        return self._w3.to_wei(amount, unit_name)

    async def _get_native_balance(self):
        balance = await self._w3.eth.get_balance(self._address)

        return balance / (10 ** 18)

    async def _send_transaction(self, transaction):
        signed_tx = self._w3.eth.account.sign_transaction(transaction, self._private)
        tx_hash = self._w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return tx_hash

    async def _wait_tx(self, *, hex_bytes: HexBytes):
        total_time = 0
        timeout = 60
        poll_latency = 10
        tx_hash: str = hex_bytes.hex()

        while True:
            try:
                receipts = await self._w3.eth.get_transaction_receipt(HexStr(tx_hash))
                status = receipts.get("status")
                if status == 1:
                    print(f"Transaction was successful: {self._chain.get("explorer_url")}tx/0x{hex_bytes.hex()}")
                    return True
                elif status is None:
                    await asyncio.sleep(poll_latency)
                else:
                    print(f"Transaction failed: {self._chain.get("explorer_url")}tx/0x{hex_bytes.hex()}")
                    return False
            except TransactionNotFound:
                if total_time > timeout:
                    print(f"Transaction isn`t in the chain after {timeout} seconds")
                    return False
                total_time += poll_latency
                await asyncio.sleep(poll_latency)