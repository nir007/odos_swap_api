from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.types import HexBytes, HexStr, TxParams, Wei
from web3.exceptions import TransactionNotFound
from typing import cast
import asyncio
import json
from colorama import Fore, Style

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
        self._account_address = self._w3.to_checksum_address(
            self._w3.eth.account.from_key(private).address
        )

    def _to_wei(self, *, amount: float, decimals: int) -> int:
        unit_name = {
            6: "mwei",
            9: "gwei",
            18: "ether",
        }.get(decimals)

        if not unit_name:
            raise RuntimeError(f"Can`t find unit for decimals: {decimals}")

        return self._w3.to_wei(amount, unit_name)

    async def _get_native_balance(self):
        balance = await self._w3.eth.get_balance(self._account_address)

        return balance / (10 ** 18)

    async def _send_transaction(self, transaction):
        signed_tx = self._w3.eth.account.sign_transaction(transaction, self._private)
        tx_hash = await self._w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return tx_hash

    def _get_contract(self, token_address: str, abi):
        return self._w3.eth.contract(
            address=self._w3.to_checksum_address(token_address),
            abi=abi
        )

    def __load_abi(self):
        try:
            with open(self._chain.get("abi")) as file:
                return json.load(file)
        except Exception as e:
            raise RuntimeError(f"Can`t abi file {self._chain.get("abi")} {e}")

    async def _prepare_tx(self) -> TxParams:
        base_fee = await self._w3.eth.gas_price
        max_priority_fee_per_gas = await self._w3.eth.max_priority_fee
        max_fee_per_gas = int(base_fee + max_priority_fee_per_gas)

        trx: TxParams = {
            "from": self._account_address,
            "chainId": await self._w3.eth.chain_id,
            "nonce": await self._w3.eth.get_transaction_count(self._account_address),
            "maxPriorityFeePerGas": max_priority_fee_per_gas,
            "maxFeePerGas": cast(Wei, max_fee_per_gas),
            "type": HexStr("0x2")
        }

        return trx

    async def _approve(self, token_name: str, amount_in_wai: int):
        abi = self.__load_abi()

        token_address = self._chain.get(token_name).get("contract")

        transaction = await self._get_contract(token_address=token_address, abi=abi).functions.approve(
            self._account_address,
            amount_in_wai
        ).build_transaction(await self._prepare_tx())

        print(Fore.GREEN + f"Approving swap {token_name.upper()} for account {self._account_address}")
        print(Style.RESET_ALL)

        return await self._send_transaction(transaction)

    def _is_native_token(self, token_name: str) -> bool:
        return token_name.lower() == str(self._chain.get("native_token")).lower()

    async def _sign(self, transaction: dict) -> HexBytes:
        signed_transaction = self._w3.eth.account.sign_transaction(transaction, self._private)
        return signed_transaction.raw_transaction

    async def _wait_tx(self, *, hex_bytes: HexBytes):
        total_time = 0
        timeout = 80
        poll_latency = 10
        tx_hash: str = hex_bytes.hex()

        while True:
            try:
                print("Checking transaction status...")

                receipts = await self._w3.eth.get_transaction_receipt(HexStr(tx_hash))
                status = receipts.get("status")
                if status == 1:
                    print(Fore.GREEN + f"Transaction was successful: {self._chain.get('explorer_url')}tx/0x{hex_bytes.hex()}")
                    print(Style.RESET_ALL)
                    return True
                elif status is None:
                    await asyncio.sleep(poll_latency)
                else:
                    print(Fore.RED + f"Transaction failed: {self._chain.get('explorer_url')}tx/0x{hex_bytes.hex()}")
                    print(Style.RESET_ALL)
                    return False
            except TransactionNotFound:
                if total_time > timeout:
                    print(Fore.RED + f"Transaction isn`t in the chain after {timeout} seconds")
                    print(Style.RESET_ALL)
                    return False
                total_time += poll_latency
                await asyncio.sleep(poll_latency)