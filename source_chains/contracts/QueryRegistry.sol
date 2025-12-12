// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/// @title QueryRegistry
/// @notice 记录评分轮次（rid）到文档 ID 的绑定，以及链上累加的承诺 Com_sum
/// @dev 与设计文档对齐：Data Chain 暴露 Com_sum^(j,d) 给 Aggregator Chain 读取，无需链上 tally。
contract QueryRegistry {
    struct Query {
        uint256 docId;       // 被评分的文档标识
        bytes32 comSum;      // 链上累加的承诺 Com_sum^(j,d)
        bytes32 listHash;    // （可选）链下承诺列表的绑定哈希，便于审计
        uint64 openedAt;     // 轮次开启时间戳
        bool finalized;      // 一旦标记，视为该 rid 聚合完毕
    }

    address public owner;
    mapping(bytes32 => Query) public queries;

    event OwnerUpdated(address indexed oldOwner, address indexed newOwner);
    event QueryOpened(bytes32 indexed rid, uint256 indexed docId);
    event ComSumRecorded(bytes32 indexed rid, bytes32 comSum, bytes32 listHash);
    event QueryFinalized(bytes32 indexed rid);

    modifier onlyOwner() {
        require(msg.sender == owner, "QueryRegistry: not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        emit OwnerUpdated(address(0), msg.sender);
    }

    /// @notice 更新合约 owner
    function setOwner(address newOwner) external onlyOwner {
        require(newOwner != address(0), "QueryRegistry: zero owner");
        emit OwnerUpdated(owner, newOwner);
        owner = newOwner;
    }

    /// @notice 为某个 rid 绑定文档，开启一个新的评分轮次
    function openQuery(bytes32 rid, uint256 docId) external onlyOwner {
        require(rid != bytes32(0), "QueryRegistry: rid=0");
        Query storage q = queries[rid];
        require(q.openedAt == 0, "QueryRegistry: exists");

        q.docId = docId;
        q.openedAt = uint64(block.timestamp);

        emit QueryOpened(rid, docId);
    }

    /// @notice 记录该 rid 下的累加承诺 Com_sum^(j,d)
    /// @param rid      轮次标识
    /// @param comSum   Pedersen 承诺和（链下通过同态求和得到）
    /// @param listHash 可选：链下承诺列表的绑定哈希，便于审核
    function recordComSum(bytes32 rid, bytes32 comSum, bytes32 listHash) external onlyOwner {
        Query storage q = queries[rid];
        require(q.openedAt != 0, "QueryRegistry: unknown rid");
        require(!q.finalized, "QueryRegistry: finalized");
        require(comSum != bytes32(0), "QueryRegistry: comSum=0");

        q.comSum = comSum;
        q.listHash = listHash;

        emit ComSumRecorded(rid, comSum, listHash);
    }

    /// @notice 将某轮次标记为已完成，阻止后续覆盖
    function finalize(bytes32 rid) external onlyOwner {
        Query storage q = queries[rid];
        require(q.openedAt != 0, "QueryRegistry: unknown rid");
        require(!q.finalized, "QueryRegistry: finalized");
        q.finalized = true;
        emit QueryFinalized(rid);
    }
}
