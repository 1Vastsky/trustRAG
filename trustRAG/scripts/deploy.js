const hre = require("hardhat");

async function main() {
  const signers = await hre.ethers.getSigners();
  const committee = signers.slice(0, 3).map((s) => s.address);
  const threshold = 2;

  const factory = await hre.ethers.getContractFactory("DataChain");
  const contract = await factory.deploy(committee, threshold);
  await contract.waitForDeployment();
  console.log("DataChain deployed to:", await contract.getAddress());
  console.log("Committee:", committee, "threshold:", threshold);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
