const hre = require("hardhat");

async function main() {
  const factory = await hre.ethers.getContractFactory("DataChain");
  const contract = await factory.deploy();
  await contract.waitForDeployment();
  console.log("DataChain deployed to:", await contract.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
