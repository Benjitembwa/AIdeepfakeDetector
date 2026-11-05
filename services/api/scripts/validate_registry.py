"""Validate the open Base Sepolia registry used by browser wallets."""

import asyncio

from web3 import AsyncHTTPProvider, AsyncWeb3, Web3

from app.core.config import get_settings
from app.services.blockchain import REGISTRY_ABI


async def main() -> None:
    settings = get_settings()
    web3 = AsyncWeb3(AsyncHTTPProvider(settings.base_rpc_url))
    address = Web3.to_checksum_address(settings.registry_contract_address)
    contract = web3.eth.contract(address=address, abi=REGISTRY_ABI)

    chain_id = await web3.eth.chain_id
    code = await web3.eth.get_code(address)
    registration_open = bool(await contract.functions.registrationOpen().call())
    print("CHAIN_ID", chain_id)
    print("BYTECODE_BYTES", len(code))
    print("CONTRACT", address)
    print("REGISTRATION_OPEN", registration_open)

    if chain_id != settings.base_chain_id:
        raise RuntimeError("The RPC chain ID does not match the configuration")
    if not code:
        raise RuntimeError("The registry has no bytecode")
    if not registration_open:
        raise RuntimeError("The configured registry is not open to browser wallets")


if __name__ == "__main__":
    asyncio.run(main())
