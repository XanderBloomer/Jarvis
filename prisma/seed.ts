import { PrismaClient } from "@prisma/client";

// Import player list from team config
// Note: can't use path aliases in seed script, so relative import
const PLAYERS = [
  "Jason Tame",
  "Mark Kingswell",
  "Adam Gillen",
  "Charlie Cripps",
  "Justin Andrews",
  "Lee Paice",
  "Lewis Johnson",
  "Matt James",
  "Xander Bloomer",
];

const prisma = new PrismaClient();

async function main() {
  console.log("Seeding players...");

  for (const name of PLAYERS) {
    await prisma.player.upsert({
      where: { name },
      update: {},
      create: { name },
    });
  }

  console.log(`Seeded ${PLAYERS.length} players`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
