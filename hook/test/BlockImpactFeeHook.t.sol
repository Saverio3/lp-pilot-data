// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {Test} from "forge-std/Test.sol";
import {Deployers} from "@uniswap/v4-core/test/utils/Deployers.sol";
import {IHooks} from "@uniswap/v4-core/src/interfaces/IHooks.sol";
import {Hooks} from "@uniswap/v4-core/src/libraries/Hooks.sol";
import {IPoolManager} from "@uniswap/v4-core/src/interfaces/IPoolManager.sol";
import {PoolKey} from "@uniswap/v4-core/src/types/PoolKey.sol";
import {BalanceDelta} from "@uniswap/v4-core/src/types/BalanceDelta.sol";
import {LPFeeLibrary} from "@uniswap/v4-core/src/libraries/LPFeeLibrary.sol";
import {TickMath} from "@uniswap/v4-core/src/libraries/TickMath.sol";
import {SwapParams, ModifyLiquidityParams} from "@uniswap/v4-core/src/types/PoolOperation.sol";
import {BlockImpactFeeHook} from "../src/BlockImpactFeeHook.sol";

contract BlockImpactFeeHookTest is Test, Deployers {
    BlockImpactFeeHook hook;
    uint24 constant BASE = 3000; // 0.30%
    uint256 constant GAMMA = 1e18; // tested setting
    uint24 constant CAP = 100000; // 10%
    uint256 constant L = 1e24; // full-range liquidity -> virtual reserves of 1e24 each at price 1

    function setUp() public {
        deployFreshManagerAndRouters();
        deployMintAndApprove2Currencies();
        address flags = address(uint160(Hooks.BEFORE_SWAP_FLAG | Hooks.AFTER_INITIALIZE_FLAG) ^ (0x4444 << 144));
        deployCodeTo("BlockImpactFeeHook.sol:BlockImpactFeeHook", abi.encode(manager, BASE, GAMMA, CAP), flags);
        hook = BlockImpactFeeHook(flags);
        (key,) = initPool(currency0, currency1, IHooks(address(hook)), LPFeeLibrary.DYNAMIC_FEE_FLAG, SQRT_PRICE_1_1);
        modifyLiquidityRouter.modifyLiquidity(
            key,
            ModifyLiquidityParams({
                tickLower: TickMath.minUsableTick(key.tickSpacing),
                tickUpper: TickMath.maxUsableTick(key.tickSpacing),
                liquidityDelta: int256(L),
                salt: 0
            }),
            ZERO_BYTES
        );
    }

    function _params(bool zeroForOne, int256 amount) internal pure returns (SwapParams memory) {
        return SwapParams({
            zeroForOne: zeroForOne,
            amountSpecified: amount,
            sqrtPriceLimitX96: zeroForOne ? TickMath.MIN_SQRT_PRICE + 1 : TickMath.MAX_SQRT_PRICE - 1
        });
    }

    /// exact-input swap; returns the fee the hook charged and the output received
    function _swapIn(bool zeroForOne, uint256 amountIn) internal returns (uint24 fee, uint256 out) {
        fee = hook.quoteFee(key, _params(zeroForOne, -int256(amountIn)));
        BalanceDelta d = swap(key, zeroForOne, -int256(amountIn), ZERO_BYTES);
        out = zeroForOne ? uint256(int256(d.amount1())) : uint256(int256(d.amount0()));
    }

    function test_smallTrade_paysBaseFee() public {
        (uint24 fee,) = _swapIn(true, 1e18); // 0.0001% of the pool
        assertLe(fee, BASE + 2, "small trade should pay ~0.30%");
    }

    function test_bigTrade_paysSizeFee() public {
        (uint24 fee,) = _swapIn(true, 1e22); // 1% of the pool -> +1% extra
        assertApproxEqAbs(fee, BASE + 10000, 20, "1% trade should pay 0.30% + 1%");
    }

    function test_feeIsSameForSplitTrades() public {
        uint256 snap = vm.snapshotState();
        (uint24 f1, uint256 outSingle) = _swapIn(true, 1e22);
        uint256 feesSingle = uint256(1e22) * f1 / 1e6;
        vm.revertToState(snap);
        uint256 feesSplit;
        uint256 outSplit;
        for (uint256 i; i < 10; i++) {
            (uint24 f, uint256 o) = _swapIn(true, 1e21);
            feesSplit += uint256(1e21) * f / 1e6;
            outSplit += o;
        }
        assertApproxEqRel(feesSplit, feesSingle, 0.02e18, "splitting must not reduce total fees (within 2%)");
        assertApproxEqRel(outSplit, outSingle, 0.001e18, "splitting must not give a better price");
    }

    function test_newBlock_resetsFlow() public {
        _swapIn(true, 1e22);
        vm.roll(block.number + 1);
        (uint24 fee,) = _swapIn(true, 1e18);
        assertLe(fee, BASE + 2, "flow resets every block");
    }

    function test_tradeAgainstTheFlow_paysBaseFee() public {
        _swapIn(true, 1e22); // bot pushes one way
        (uint24 fee,) = _swapIn(false, 1e20); // normal trader goes the other way in the same block
        assertEq(fee, BASE, "trades that reduce the block's imbalance pay only the base fee");
    }

    function test_feeIsCapped() public {
        (uint24 fee,) = _swapIn(true, 3e23); // 30% of the pool
        assertEq(fee, CAP);
    }

    function test_sameFeeBothDirections() public {
        uint24 a = hook.quoteFee(key, _params(true, -1e22));
        uint24 b = hook.quoteFee(key, _params(false, -1e22));
        assertApproxEqAbs(a, b, 2);
    }

    function test_exactOutput_chargedLikeExactInput() public {
        uint24 a = hook.quoteFee(key, _params(true, -1e22));
        uint24 b = hook.quoteFee(key, _params(true, 1e22));
        assertApproxEqAbs(a, b, 2);
    }

    function testFuzz_feeWithinBounds(bool zeroForOne, uint256 amount) public {
        amount = bound(amount, 1e6, 2e23);
        (uint24 fee,) = _swapIn(zeroForOne, amount);
        assertGe(fee, BASE);
        assertLe(fee, CAP);
    }

    function test_staticFeePool_reverts() public {
        vm.expectRevert();
        initPool(currency0, currency1, IHooks(address(hook)), 3000, SQRT_PRICE_1_2);
    }

    function test_badConfig_reverts() public {
        vm.expectRevert();
        this.deployWithBadConfig();
    }

    function deployWithBadConfig() external {
        address other = address(uint160(Hooks.BEFORE_SWAP_FLAG | Hooks.AFTER_INITIALIZE_FLAG) ^ (0x5555 << 144));
        deployCodeTo("BlockImpactFeeHook.sol:BlockImpactFeeHook", abi.encode(manager, uint24(5000), GAMMA, uint24(4000)), other);
    }
}
