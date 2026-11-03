// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {BaseOverrideFee} from "@openzeppelin/uniswap-hooks/fee/BaseOverrideFee.sol";
import {BaseHook} from "@openzeppelin/uniswap-hooks/base/BaseHook.sol";
import {IPoolManager} from "@uniswap/v4-core/src/interfaces/IPoolManager.sol";
import {PoolKey} from "@uniswap/v4-core/src/types/PoolKey.sol";
import {PoolId, PoolIdLibrary} from "@uniswap/v4-core/src/types/PoolId.sol";
import {SwapParams} from "@uniswap/v4-core/src/types/PoolOperation.sol";
import {StateLibrary} from "@uniswap/v4-core/src/libraries/StateLibrary.sol";
import {FullMath} from "@uniswap/v4-core/src/libraries/FullMath.sol";
import {FixedPoint96} from "@uniswap/v4-core/src/libraries/FixedPoint96.sol";

/// @title BlockImpactFeeHook ("Earn")
/// @notice Uniswap v4 dynamic-fee hook. Normal traders pay the base fee (0.30%). Trades that push the pool's price
///         further in one direction within the same block pay an extra fee proportional to how far the block's
///         combined flow has moved the pool. Arbitrage bots correcting a stale price make large one-directional
///         moves, so they pay most of the extra; small trades pay ~the base fee.
/// @dev    No external price feed (oracle-free). The extra fee uses the block's cumulative net flow, priced with the
///         rule  rate = gamma * (|flow before| + |flow after|).  With this rule the total extra fee is the SAME whether a
///         trader makes one big swap or splits it into many small swaps in the same block (split-proof), and a single
///         swap of size s pays rate gamma * s, matching the simulated design ("trade-size fee, per block").
///         Flow is measured as a fraction of the pool's virtual reserve of the input (or output) token at the current
///         price and active liquidity (full-range approximation; with concentrated liquidity it measures local depth).
contract BlockImpactFeeHook is BaseOverrideFee {
    using PoolIdLibrary for PoolKey;
    using StateLibrary for IPoolManager;

    uint256 internal constant WAD = 1e18;
    uint256 internal constant PIPS = 1e6; // fee units: 1e6 = 100%

    /// @notice Fee every swap pays, in hundredths of a bip (3000 = 0.30%).
    uint24 public immutable baseFee;
    /// @notice Strength of the size fee (1e18 = 1.0, the tested setting).
    uint256 public immutable gammaWad;
    /// @notice Upper limit on the total fee (e.g. 100000 = 10%).
    uint24 public immutable maxFee;

    struct BlockFlow {
        uint64 blockNumber;
        int192 netFlowWad; // signed: + = token0 into the pool, - = token1 into the pool; 1e18 = 100% of virtual reserve
    }

    mapping(PoolId => BlockFlow) public blockFlow;

    event FeeApplied(PoolId indexed poolId, uint24 fee, int256 netFlowBeforeWad, int256 netFlowAfterWad);

    error InvalidConfig();

    constructor(IPoolManager _poolManager, uint24 _baseFee, uint256 _gammaWad, uint24 _maxFee) BaseHook(_poolManager) {
        if (_baseFee > _maxFee || _maxFee > PIPS) revert InvalidConfig();
        baseFee = _baseFee;
        gammaWad = _gammaWad;
        maxFee = _maxFee;
    }

    /// @notice Fee a swap would pay right now (view helper for routers, UIs and tests).
    function quoteFee(PoolKey calldata key, SwapParams calldata params) external view returns (uint24 fee) {
        (fee,,) = _compute(key, params);
    }

    function _getFee(address, PoolKey calldata key, SwapParams calldata params, bytes calldata)
        internal
        override
        returns (uint24 fee)
    {
        int256 before;
        int256 after_;
        (fee, before, after_) = _compute(key, params);
        PoolId id = key.toId();
        int256 lim = int256(type(int192).max);
        int256 stored = after_ > lim ? lim : (after_ < -lim ? -lim : after_);
        blockFlow[id] = BlockFlow(uint64(block.number), int192(stored));
        emit FeeApplied(id, fee, before, after_);
    }

    function _compute(PoolKey calldata key, SwapParams calldata params)
        internal
        view
        returns (uint24 fee, int256 before, int256 after_)
    {
        PoolId id = key.toId();
        BlockFlow memory f = blockFlow[id];
        before = f.blockNumber == block.number ? int256(f.netFlowWad) : int256(0);
        after_ = before + _flowFraction(id, params);

        uint256 total = baseFee;
        uint256 ab = _abs(before);
        uint256 aa = _abs(after_);
        if (aa > ab) {
            // only swaps that push the pool further away within this block pay extra
            uint256 rateWad = (before == 0 || (before > 0) == (after_ > 0)) ? ab + aa : aa;
            uint256 extraWad = FullMath.mulDiv(gammaWad, rateWad, WAD);
            total += FullMath.mulDiv(extraWad, PIPS, WAD);
        }
        fee = total > maxFee ? maxFee : uint24(total);
    }

    /// @dev Signed size of this swap as a fraction (WAD) of the virtual reserve of the token it is measured in.
    ///      zeroForOne (token0 in)  -> positive; oneForZero (token1 in) -> negative.
    function _flowFraction(PoolId id, SwapParams calldata params) internal view returns (int256) {
        uint128 liquidity = poolManager.getLiquidity(id);
        if (liquidity == 0) return 0;
        (uint160 sqrtPriceX96,,,) = poolManager.getSlot0(id);
        bool exactIn = params.amountSpecified < 0;
        uint256 amount = exactIn ? uint256(-params.amountSpecified) : uint256(params.amountSpecified);
        // exact-in zeroForOne: token0 amount; exact-out zeroForOne: token1 amount (and mirrored for oneForZero)
        bool measuredInToken0 = params.zeroForOne == exactIn;
        uint256 frac;
        if (measuredInToken0) {
            // virtual reserve x = L * 2^96 / sqrtP  ->  amount / x = amount * sqrtP / (L * 2^96)
            frac = FullMath.mulDiv(FullMath.mulDiv(amount, sqrtPriceX96, liquidity), WAD, FixedPoint96.Q96);
        } else {
            // virtual reserve y = L * sqrtP / 2^96  ->  amount / y = amount * 2^96 / (L * sqrtP)
            frac = FullMath.mulDiv(FullMath.mulDiv(amount, FixedPoint96.Q96, sqrtPriceX96), WAD, liquidity);
        }
        uint256 maxFrac = uint256(int256(type(int192).max));
        if (frac > maxFrac) frac = maxFrac;
        return params.zeroForOne ? int256(frac) : -int256(frac);
    }

    function _abs(int256 v) internal pure returns (uint256) {
        return v >= 0 ? uint256(v) : uint256(-v);
    }
}
