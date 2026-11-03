# Earn hook (BlockImpactFeeHook)

A Uniswap v4 dynamic-fee hook. Normal traders pay **0.30%** (same as a standard Uniswap pool). Trades that push the
pool's price further in one direction **within the same block** pay an extra fee proportional to how far the block's
combined flow has moved the pool — this is what arbitrage bots do when they correct a stale pool price.

- **No price feed (oracle-free):** the hook only looks at the pool's own state.
- **Split-proof:** the extra fee uses the rule `rate = gamma × (|flow before| + |flow after|)`, so one big swap and the
  same amount split into many small swaps in one block pay the same total fee (tested).
- **Normal traders protected:** small trades and trades against the block's flow pay only the base fee (tested).
- Settings (constructor): `baseFee` 3000 (0.30%), `gamma` 1e18, `maxFee` 100000 (10%).

## Tests
```
cd hook && forge test -vv
```
| Test | What it proves |
|---|---|
| test_smallTrade_paysBaseFee | small trade pays ~0.30% |
| test_bigTrade_paysSizeFee | a trade of 1% of the pool pays 0.30% + 1% |
| test_feeIsSameForSplitTrades | 10 small swaps in one block pay the same total fee as 1 big swap; no better price |
| test_newBlock_resetsFlow | the flow measure resets every block |
| test_tradeAgainstTheFlow_paysBaseFee | a trade reducing the block's imbalance pays only 0.30% |
| test_feeIsCapped | fee never exceeds the cap |
| test_sameFeeBothDirections / test_exactOutput_chargedLikeExactInput | symmetric, exact-in = exact-out |
| testFuzz_feeWithinBounds | 256 random trades: fee always between base and cap |
| test_staticFeePool_reverts, test_badConfig_reverts | safety checks |

## Deploy to Unichain Sepolia (testnet)
1. Create a **new** wallet for testnets only and get free Unichain Sepolia ETH from a faucet.
2. Add its private key as repository secret `TESTNET_PRIVATE_KEY`.
3. Actions tab → **deploy-testnet** → Run workflow. The bot deploys the hook, two test tokens, a hooked pool and a
   plain 0.30% pool side by side, runs a small and a big demo trade in each, and saves the addresses to
   `hook/deployments/unichain-sepolia.txt`.

Local dry run: `anvil` then `PRIVATE_KEY=<anvil key> LOCAL=true forge script script/DeployTestnet.s.sol --rpc-url http://127.0.0.1:8545 --broadcast`.

Not audited. Testnet only.
