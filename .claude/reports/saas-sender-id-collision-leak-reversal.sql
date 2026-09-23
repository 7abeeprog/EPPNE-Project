-- عكس تسريب regression جلسة saas-sender-id-collision-fix (§14.5، §15.2)
-- tx 1045/1046 (FINBIND، بند test-financeservice-tenant-binding-leaks-user1-funds)
-- tx 1047 (TRIGREN، تسريب غير مسجَّل سابقًا — §16.6)
-- كل خطوة مُحرَسة بالقيمة الحالية بالضبط؛ أي rowcount غير متوقع = RAISE → ROLLBACK كامل.
\set ON_ERROR_STOP on
BEGIN;

DO $$
DECLARE n integer;
BEGIN
  UPDATE wallets SET balances = jsonb_set(balances, '{MR_USDT}', to_jsonb(702.0))
   WHERE id = 39 AND user_id = 1 AND (balances->>'MR_USDT')::numeric = 699.0;
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 1 THEN RAISE EXCEPTION 'wallet 39: rowcount % (expected 1)', n; END IF;

  UPDATE wallets SET balances = jsonb_set(balances, '{MR_USDT}', to_jsonb(173.0))
   WHERE id = 929 AND user_id = 957 AND (balances->>'MR_USDT')::numeric = 176.0;
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 1 THEN RAISE EXCEPTION 'wallet 929: rowcount % (expected 1)', n; END IF;

  DELETE FROM audit_logs WHERE id IN (1027, 1028, 1029) AND user_id = 1 AND action = 'TRANSFER';
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 3 THEN RAISE EXCEPTION 'audit_logs: rowcount % (expected 3)', n; END IF;

  DELETE FROM transactions WHERE id IN (1045, 1046, 1047) AND sender_id = 1 AND receiver_id = 957 AND amount = 1;
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 3 THEN RAISE EXCEPTION 'transactions: rowcount % (expected 3)', n; END IF;
END $$;

-- تحقق قبل COMMIT
SELECT 'pre-commit' AS stage,
       (SELECT balances->>'MR_USDT' FROM wallets WHERE id = 39)  AS w39,
       (SELECT balances->>'MR_USDT' FROM wallets WHERE id = 929) AS w929,
       (SELECT max(id) FROM transactions) AS max_tx;

DO $$
BEGIN
  IF (SELECT (balances->>'MR_USDT')::numeric FROM wallets WHERE id = 39) <> 702.0
     OR (SELECT (balances->>'MR_USDT')::numeric FROM wallets WHERE id = 929) <> 173.0
     OR (SELECT max(id) FROM transactions) <> 1037 THEN
    RAISE EXCEPTION 'pre-commit verification failed';
  END IF;
END $$;

COMMIT;
