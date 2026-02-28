// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title DataChain
/// @notice Demo chain state for vote commitment products by (docId, roundId).
contract DataChain {
    uint256 public constant P = 170141183460469231731687303715884105727; // 2^127 - 1
    uint256 public constant G = 5;
    uint256 public constant H = 7;

    mapping(string => mapping(uint256 => uint256)) private _productCommitment;
    mapping(string => mapping(uint256 => uint256)) public voteCount;

    event VoteSubmitted(string indexed docId, uint256 indexed rid, uint256 commitment, uint256 newProduct);

    function submitVote(string calldata docId, uint256 rid, uint256 commitment) external {
        require(commitment > 0 && commitment < P, "invalid commitment");
        uint256 current = _productCommitment[docId][rid];
        if (current == 0) {
            current = 1;
        }
        uint256 updated = mulmod(current, commitment, P);
        _productCommitment[docId][rid] = updated;
        voteCount[docId][rid] += 1;
        emit VoteSubmitted(docId, rid, commitment, updated);
    }

    function getProduct(string calldata docId, uint256 rid) public view returns (uint256) {
        uint256 product = _productCommitment[docId][rid];
        return product == 0 ? 1 : product;
    }
}
