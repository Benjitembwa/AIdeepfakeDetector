import type { WalletTransaction } from "@/lib/api";

export const BASE_SEPOLIA_CHAIN_ID = "0x14a34";

type EthereumRequest = { method: string; params?: unknown[] };

export type EthereumProvider = {
  request: (request: EthereumRequest) => Promise<unknown>;
  on?: (event: string, listener: (...args: unknown[]) => void) => void;
  removeListener?: (event: string, listener: (...args: unknown[]) => void) => void;
};

declare global {
  interface Window { ethereum?: EthereumProvider }
}

export class WalletError extends Error {}

export function getWalletProvider(): EthereumProvider | null {
  return typeof window === "undefined" ? null : window.ethereum ?? null;
}

function firstAccount(value: unknown): string | null {
  return Array.isArray(value) && typeof value[0] === "string" ? value[0] : null;
}

export async function currentWallet(): Promise<{ address: string | null; chainId: string | null }> {
  const provider = getWalletProvider();
  if (!provider) return { address: null, chainId: null };
  const [accounts, chainId] = await Promise.all([
    provider.request({ method: "eth_accounts" }),
    provider.request({ method: "eth_chainId" }),
  ]);
  return {
    address: firstAccount(accounts),
    chainId: typeof chainId === "string" ? chainId.toLowerCase() : null,
  };
}

export async function ensureBaseSepolia(provider: EthereumProvider): Promise<void> {
  const chainId = await provider.request({ method: "eth_chainId" });
  if (typeof chainId === "string" && chainId.toLowerCase() === BASE_SEPOLIA_CHAIN_ID) return;
  try {
    await provider.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: BASE_SEPOLIA_CHAIN_ID }],
    });
  } catch (reason) {
    const code = typeof reason === "object" && reason && "code" in reason ? Number(reason.code) : 0;
    if (code !== 4902) throw new WalletError("Le passage vers Base Sepolia a été refusé.");
    await provider.request({
      method: "wallet_addEthereumChain",
      params: [{
        chainId: BASE_SEPOLIA_CHAIN_ID,
        chainName: "Base Sepolia",
        nativeCurrency: { name: "Ether", symbol: "ETH", decimals: 18 },
        rpcUrls: ["https://sepolia.base.org"],
        blockExplorerUrls: ["https://sepolia.basescan.org"],
      }],
    });
  }
}

export async function connectWallet(): Promise<string> {
  const provider = getWalletProvider();
  if (!provider) throw new WalletError("MetaMask n’est pas installé dans ce navigateur.");
  const accounts = await provider.request({ method: "eth_requestAccounts" });
  const address = firstAccount(accounts);
  if (!address) throw new WalletError("Aucun compte MetaMask n’a été autorisé.");
  await ensureBaseSepolia(provider);
  return address;
}

export async function sendWalletTransaction(transaction: WalletTransaction): Promise<string> {
  const provider = getWalletProvider();
  if (!provider) throw new WalletError("MetaMask n’est pas installé dans ce navigateur.");
  await ensureBaseSepolia(provider);
  const accounts = await provider.request({ method: "eth_accounts" });
  const address = firstAccount(accounts);
  if (!address || address.toLowerCase() !== transaction.from_address.toLowerCase()) {
    throw new WalletError("Sélectionnez dans MetaMask le portefeuille lié à cette preuve.");
  }
  const txHash = await provider.request({
    method: "eth_sendTransaction",
    params: [{
      from: address,
      to: transaction.contract_address,
      data: transaction.data,
      value: transaction.value,
    }],
  });
  if (typeof txHash !== "string") throw new WalletError("MetaMask n’a pas renvoyé de transaction.");
  return txHash;
}

export async function waitForWalletReceipt(
  txHash: string,
  timeoutMs = 120_000,
): Promise<void> {
  const provider = getWalletProvider();
  if (!provider) throw new WalletError("MetaMask n’est pas installé dans ce navigateur.");
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const receipt = await provider.request({
      method: "eth_getTransactionReceipt",
      params: [txHash],
    }) as { status?: string } | null;
    if (receipt) {
      if (receipt.status === "0x1") return;
      throw new WalletError("La transaction a été refusée par Base Sepolia.");
    }
    await new Promise(resolve => setTimeout(resolve, 2_000));
  }
  throw new WalletError("La transaction est toujours en attente. Vous pourrez reprendre plus tard.");
}
