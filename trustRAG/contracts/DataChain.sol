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
    mapping(string => mapping(uint256 => uint256)) public aggregatedS;
    mapping(string => mapping(uint256 => uint256)) public aggregatedR;
    mapping(string => mapping(uint256 => uint256)) public aggregatedVoteCount;
    mapping(string => mapping(uint256 => bytes32)) public aggregatedSigmaHash;

    mapping(address => bool) public isCommitteeMember;
    uint256 public committeeThreshold;

    event VoteSubmitted(string indexed docId, uint256 indexed rid, uint256 commitment, uint256 newProduct);
    event AggregateSubmitted(
        string indexed docId,
        uint256 indexed rid,
        uint256 S,
        uint256 R,
        uint256 voteCount,
        bytes32 sigmaHash
    );

    constructor(address[] memory committeeMembers, uint256 threshold) {
        require(committeeMembers.length > 0, "committee required");
        require(threshold > 0 && threshold <= committeeMembers.length, "invalid threshold");
        for (uint256 i = 0; i < committeeMembers.length; i++) {
            isCommitteeMember[committeeMembers[i]] = true;
        }
        committeeThreshold = threshold;
    }

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

    function submitAggregate(
        string calldata docId,
        uint256 rid,
        uint256 S,
        uint256 R,
        uint256 voteCount_,
        bytes calldata sigma,
        bytes[] calldata attestations
    ) external {
        require(voteCount_ > 0, "empty votes");
        require(voteCount[docId][rid] == voteCount_, "vote count mismatch");

        bytes32 digest = _attestationDigest(docId, rid, S, R, voteCount_, sigma);
        require(_verifyAttestation(digest, attestations), "insufficient committee attestations");

        uint256 left = mulmod(modexp(G, S, P), modexp(H, R, P), P);
        require(left == getProduct(docId, rid), "pedersen equation failed");

        aggregatedS[docId][rid] = S % P;
        aggregatedR[docId][rid] = R % P;
        aggregatedVoteCount[docId][rid] = voteCount_;
        aggregatedSigmaHash[docId][rid] = keccak256(sigma);

        emit AggregateSubmitted(docId, rid, S % P, R % P, voteCount_, keccak256(sigma));
    }

    function modexp(uint256 base, uint256 exponent, uint256 modulus) public pure returns (uint256) {
        require(modulus != 0, "modulus is zero");
        uint256 result = 1 % modulus;
        uint256 b = base % modulus;
        uint256 e = exponent;
        while (e > 0) {
            if ((e & 1) == 1) {
                result = mulmod(result, b, modulus);
            }
            e >>= 1;
            b = mulmod(b, b, modulus);
        }
        return result;
    }

    function _attestationDigest(
        string calldata docId,
        uint256 rid,
        uint256 S,
        uint256 R,
        uint256 voteCount_,
        bytes calldata sigma
    ) internal view returns (bytes32) {
        return keccak256(abi.encode(address(this), block.chainid, docId, rid, S, R, voteCount_, keccak256(sigma)));
    }

    function _verifyAttestation(bytes32 digest, bytes[] calldata attestations) internal view returns (bool) {
        bytes32 ethDigest = _toEthSignedMessageHash(digest);
        uint256 valid = 0;
        address[] memory seen = new address[](attestations.length);

        for (uint256 i = 0; i < attestations.length; i++) {
            address signer = _recover(ethDigest, attestations[i]);
            if (!isCommitteeMember[signer]) {
                continue;
            }
            bool duplicate = false;
            for (uint256 j = 0; j < valid; j++) {
                if (seen[j] == signer) {
                    duplicate = true;
                    break;
                }
            }
            if (duplicate) {
                continue;
            }
            seen[valid] = signer;
            valid += 1;
            if (valid >= committeeThreshold) {
                return true;
            }
        }
        return false;
    }

    function _toEthSignedMessageHash(bytes32 digest) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", digest));
    }

    function _recover(bytes32 digest, bytes calldata signature) internal pure returns (address) {
        if (signature.length != 65) {
            return address(0);
        }
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := calldataload(signature.offset)
            s := calldataload(add(signature.offset, 32))
            v := byte(0, calldataload(add(signature.offset, 64)))
        }
        if (v < 27) {
            v += 27;
        }
        if (v != 27 && v != 28) {
            return address(0);
        }
        return ecrecover(digest, v, r, s);
    }
}
