// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {Script, console2} from "forge-std/Script.sol";
import {IPoolManager} from "@uniswap/v4-core/src/interfaces/IPoolManager.sol";
import {PoolManager} from "@uniswap/v4-core/src/PoolManager.sol";
import {IHooks} from "@uniswap/v4-core/src/interfaces/IHooks.sol";
import {Hooks} from "@uniswap/v4-core/src/libraries/Hooks.sol";
import {PoolKey} from "@uniswap/v4-core/src/types/PoolKey.sol";
import {Currency} from "@uniswap/v4-core/src/types/Currency.sol";
import {LPFeeLibrary} from "@uniswap/v4-core/src/libraries/LPFeeLibrary.sol";
import {TickMath} from "@uniswap/v4-core/src/libraries/TickMath.sol";
import {SwapParams, ModifyLiquidityParams} from "@uniswap/v4-core/src/types/PoolOperation.sol";
import {PoolSwapTest} from "@uniswap/v4-core/src/test/PoolSwapTest.sol";
import {PoolModifyLiquidityTest} from "@uniswap/v4-core/src/test/PoolModifyLiquidityTest.sol";
import {MockERC20} from "solmate/src/test/utils/mocks/MockERC20.sol";
import {HookMiner} from "@uniswap/v4-periphery/src/utils/HookMiner.sol";
import {BlockImpactFeeHook} from "../src/BlockImpactFeeHook.sol";

/// Deploys the Earn hook to Unichain Sepolia (or a local node with LOCAL=1), creates two test tokens, a hooked pool and
/// a plain 0.30% pool side by side, adds liquidity, and runs a demo: one small (normal) trade and one big (bot-like)
/// trade in each pool. Prints all addresses and the fees charged.
contract DeployTestnet is Script {
    // Uniswap v4 on Unichain Sepolia (chain 1301), from developers.uniswap.org/docs/protocols/v4/deployments
    address constant POOL_MANAGER = 0x00B036B58a818B1BC34d502D3fE730Db729e62AC;
    address constant SWAP_ROUTER = 0x9140a78c1A137c7fF1c151EC8231272aF78a99A4;
    address constant LIQ_ROUTER = 0x5fa728C0A5cfd51BEe4B060773f50554c0C8A7AB;
    address constant CREATE2_DEPLOYER = 0x4e59b44847b379578588920cA78FbF26c0B4956C;

    uint24 constant BASE_FEE = 3000; // 0.30%
    uint256 constant GAMMA = 1e18;
    uint24 constant MAX_FEE = 100000; // 10%

    IPoolManager manager;
    PoolSwapTest swapRouter;
    PoolModifyLiquidityTest liqRouter;
    BlockImpactFeeHook hook;
    PoolKey hooked;
    PoolKey plain;

    function run() external {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(pk);
        _setup(vm.addr(pk), vm.envOr("LOCAL", false));
        _deployHook();
        _pools(vm.addr(pk));
        _demo();
        vm.stopBroadcast();
        console2.log("PoolManager", address(manager));
        console2.log("Hook (Earn)", address(hook));
        console2.log("token0", Currency.unwrap(hooked.currency0));
        console2.log("token1", Currency.unwrap(hooked.currency1));
        console2.log("hooked pool id");
        console2.logBytes32(keccak256(abi.encode(hooked)));
        console2.log("plain 0.30% pool id");
        console2.logBytes32(keccak256(abi.encode(plain)));
    }

    function _setup(address me, bool local) internal {
        if (local) {
            manager = new PoolManager(me);
            swapRouter = new PoolSwapTest(manager);
            liqRouter = new PoolModifyLiquidityTest(manager);
        } else {
            manager = IPoolManager(POOL_MANAGER);
            swapRouter = PoolSwapTest(SWAP_ROUTER);
            liqRouter = PoolModifyLiquidityTest(LIQ_ROUTER);
        }
    }

    // hook at an address whose bits grant beforeSwap + afterInitialize
    function _deployHook() internal {
        uint160 flags = uint160(Hooks.BEFORE_SWAP_FLAG | Hooks.AFTER_INITIALIZE_FLAG);
        bytes memory args = abi.encode(manager, BASE_FEE, GAMMA, MAX_FEE);
        (address hookAddr, bytes32 salt) = HookMiner.find(CREATE2_DEPLOYER, flags, type(BlockImpactFeeHook).creationCode, args);
        hook = new BlockImpactFeeHook{salt: salt}(manager, BASE_FEE, GAMMA, MAX_FEE);
        require(address(hook) == hookAddr, "hook address mismatch");
    }

    // two test tokens; hooked pool (dynamic fee) and plain Uniswap-style 0.30% pool with the same liquidity
    function _pools(address me) internal {
        MockERC20 a = new MockERC20("Test ETH", "tETH", 18);
        MockERC20 b = new MockERC20("Test USD", "tUSD", 18);
        (MockERC20 t0, MockERC20 t1) = address(a) < address(b) ? (a, b) : (b, a);
        t0.mint(me, 1e27);
        t1.mint(me, 1e27);
        t0.approve(address(swapRouter), type(uint256).max);
        t1.approve(address(swapRouter), type(uint256).max);
        t0.approve(address(liqRouter), type(uint256).max);
        t1.approve(address(liqRouter), type(uint256).max);
        hooked = PoolKey(Currency.wrap(address(t0)), Currency.wrap(address(t1)), LPFeeLibrary.DYNAMIC_FEE_FLAG, 60, IHooks(address(hook)));
        plain = PoolKey(Currency.wrap(address(t0)), Currency.wrap(address(t1)), 3000, 60, IHooks(address(0)));
        manager.initialize(hooked, 79228162514264337593543950336); // price 1:1
        manager.initialize(plain, 79228162514264337593543950336);
        ModifyLiquidityParams memory full = ModifyLiquidityParams(TickMath.minUsableTick(60), TickMath.maxUsableTick(60), 1e24, 0);
        liqRouter.modifyLiquidity(hooked, full, "");
        liqRouter.modifyLiquidity(plain, full, "");
    }

    // demo: a small normal trade (0.001% of pool) and a big bot-like trade (1% of pool) in each pool
    function _demo() internal {
        PoolSwapTest.TestSettings memory s = PoolSwapTest.TestSettings({takeClaims: false, settleUsingBurn: false});
        SwapParams memory small = SwapParams(true, -1e19, TickMath.MIN_SQRT_PRICE + 1);
        SwapParams memory big = SwapParams(true, -1e22, TickMath.MIN_SQRT_PRICE + 1);
        console2.log("fee small trade (pips, 3000 = 0.30%):", hook.quoteFee(hooked, small));
        swapRouter.swap(hooked, small, s, "");
        swapRouter.swap(plain, small, s, "");
        console2.log("fee big trade (pips):", hook.quoteFee(hooked, big));
        swapRouter.swap(hooked, big, s, "");
        swapRouter.swap(plain, big, s, "");
    }
}
