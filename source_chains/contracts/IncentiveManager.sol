// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/// @title IncentiveManager
/// @notice 记录每个 rid 下的奖励池与验证者领取状态，配合 QueryRegistry 的 Com_sum 数据使用
/// @dev 这里只做简化占位：owner 注入奖励金额，验证者按地址领取一次；真实系统可接入代币、比例分配或 ZK-based 资格。
contract IncentiveManager {
    struct RoundIncentive {
        uint256 amount;          // 奖励池总额（原生币，或可替换为 ERC20）
        uint64 fundedAt;
        bool finalized;          // 标记轮次结束，阻止重复注资
    }

    address public owner;
    mapping(bytes32 => RoundIncentive) public incentives;
    mapping(bytes32 => mapping(address => bool)) public claimed; // rid => validator => claimed

    event OwnerUpdated(address indexed oldOwner, address indexed newOwner);
    event IncentiveFunded(bytes32 indexed rid, uint256 amount);
    event IncentiveFinalized(bytes32 indexed rid);
    event Claimed(bytes32 indexed rid, address indexed validator, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "IncentiveManager: not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        emit OwnerUpdated(address(0), msg.sender);
    }

    function setOwner(address newOwner) external onlyOwner {
        require(newOwner != address(0), "IncentiveManager: zero owner");
        emit OwnerUpdated(owner, newOwner);
        owner = newOwner;
    }

    /// @notice 为某轮次注入奖励（简化为原生币）
    function fund(bytes32 rid) external payable onlyOwner {
        require(rid != bytes32(0), "IncentiveManager: rid=0");
        RoundIncentive storage r = incentives[rid];
        require(!r.finalized, "IncentiveManager: finalized");
        require(msg.value > 0, "IncentiveManager: zero funding");

        r.amount += msg.value;
        if (r.fundedAt == 0) {
            r.fundedAt = uint64(block.timestamp);
        }

        emit IncentiveFunded(rid, msg.value);
    }

    /// @notice 轮次结束后可标记，阻止继续注资
    function finalize(bytes32 rid) external onlyOwner {
        RoundIncentive storage r = incentives[rid];
        require(!r.finalized, "IncentiveManager: finalized");
        r.finalized = true;
        emit IncentiveFinalized(rid);
    }

    /// @notice 验证者领取奖励（均分模型，占位实现）
    /// @dev 实际应结合成员资格/证明；这里仅做一次性领取且平均分配
    function claim(bytes32 rid, address[] calldata recipients) external onlyOwner {
        RoundIncentive storage r = incentives[rid];
        require(r.amount > 0, "IncentiveManager: no funds");
        require(r.finalized, "IncentiveManager: not finalized");
        require(recipients.length > 0, "IncentiveManager: empty list");

        uint256 share = r.amount / recipients.length;
        require(share > 0, "IncentiveManager: tiny share");

        r.amount = 0; // 防重复分配

        for (uint256 i = 0; i < recipients.length; i++) {
            address to = recipients[i];
            require(!claimed[rid][to], "IncentiveManager: claimed");
            claimed[rid][to] = true;
            (bool ok, ) = to.call{value: share}("");
            require(ok, "IncentiveManager: transfer failed");
            emit Claimed(rid, to, share);
        }
    }
}
