SELECT claim_id, claim_type, amount, status
FROM claims
WHERE member_id = :member_id
ORDER BY claim_id;

