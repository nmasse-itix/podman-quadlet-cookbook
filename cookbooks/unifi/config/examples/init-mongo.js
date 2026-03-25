const authSource = process.env.MONGO_AUTHSOURCE || "admin";
const dbName = process.env.MONGO_DBNAME || "unifi";
const user = process.env.MONGO_USER || "unifi";
const pass = process.env.MONGO_PASS || "unifi";

db = db.getSiblingDB(authSource);
db.createUser({
  user: user,
  pwd: pass,
  roles: [
    { db: dbName, role: "dbOwner" },
    { db: dbName + "_stat", role: "dbOwner" },
    { db: dbName + "_audit", role: "dbOwner" }
  ]
});
