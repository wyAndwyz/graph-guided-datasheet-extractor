MATCH (u:Unit)
RETURN u.symbol AS unit
ORDER BY unit;

// Intentional failure case:
// This query only returns MVP units, while the expected schema state contains
// both MVP and variation units.

// MATCH (u:Unit)
// WHERE u.scope = "mvp"
// RETURN u.symbol AS unit
// ORDER BY unit;