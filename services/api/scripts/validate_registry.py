"""Validate the public Base Sepolia registry and the configured signer."""

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
    owner = Web3.to_checksum_address(await contract.functions.owner().call())
    balance = await web3.eth.get_balance(owner)
    print("CHAIN_ID", chain_id)
    print("BYTECODE_BYTES", len(code))
    print("OWNER", owner)
    print("OWNER_BALANCE_ETH", Web3.from_wei(balance, "ether"))

    if chain_id != settings.base_chain_id:
        raise RuntimeError("The RPC chain ID does not match the configuration")
    if not code:
        raise RuntimeError("The registry has no bytecode")

    if settings.registry_private_key is None:
        print("SIGNER_KEY", "MISSING")
        return
    signer = web3.eth.account.from_key(
        settings.registry_private_key.get_secret_value()
    ).address
    authorized = await contract.functions.authorizedPublishers(signer).call()
    print("SIGNER", signer)
    print("SIGNER_IS_OWNER", Web3.to_checksum_address(signer) == owner)
    print("SIGNER_AUTHORIZED", bool(authorized))
    if Web3.to_checksum_address(signer) != owner or not authorized:
        raise RuntimeError("The configured signer cannot publish to the registry")


if __name__ == "__main__":
    asyncio.run(main())
