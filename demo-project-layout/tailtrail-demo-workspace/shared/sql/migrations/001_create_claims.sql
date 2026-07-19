CREATE TABLE claims (
  claim_id TEXT PRIMARY KEY,
  member_id TEXT NOT NULL,
  claim_type TEXT NOT NULL,
  amount NUMERIC NOT NULL,
  status TEXT NOT NULL
);

