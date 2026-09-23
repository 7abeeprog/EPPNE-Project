BEGIN;

DO $$
DECLARE n integer;
BEGIN
    -- 1) صفّا audit_logs الخاصان بالتحويلين المسرَّبين
    DELETE FROM audit_logs
     WHERE id IN (946, 947)
       AND user_id = 1
       AND action = 'TRANSFER'
       AND details->>'tx_hash' IN ('TX-1BC7A30BC462', 'TX-83DC0E1589E9');
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 2 THEN RAISE EXCEPTION 'audit_logs: expected 2 rows, got %', n; END IF;

    -- 2) صفّا transactions المسرَّبان (1 MR_USDT لكلٍّ، user 1 -> 957)
    DELETE FROM transactions
     WHERE id IN (948, 950)
       AND sender_id = 1
       AND receiver_id = 957
       AND amount = 1
       AND currency = 'MR_USDT'
       AND idempotency_key IN ('AUTO-RENEW-851-2026-09', 'PAY-INV-161');
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 2 THEN RAISE EXCEPTION 'transactions: expected 2 rows, got %', n; END IF;

    -- 3) محفظة user 1: 708 -> 710 (فقط لو الرصيد الحالي 708 بالضبط)
    UPDATE wallets
       SET balances = jsonb_set(balances, '{MR_USDT}', to_jsonb(710.0))
     WHERE id = 39 AND user_id = 1 AND tenant_id = 1
       AND (balances->>'MR_USDT')::numeric = 708;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 1 THEN RAISE EXCEPTION 'wallet user 1: expected 1 row at 708, got %', n; END IF;

    -- 4) محفظة حساب النظام 957: 167 -> 165 (فقط لو الرصيد الحالي 167 بالضبط)
    UPDATE wallets
       SET balances = jsonb_set(balances, '{MR_USDT}', to_jsonb(165.0))
     WHERE id = 929 AND user_id = 957 AND tenant_id = 1
       AND (balances->>'MR_USDT')::numeric = 167;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 1 THEN RAISE EXCEPTION 'wallet 957: expected 1 row at 167, got %', n; END IF;
END $$;

COMMIT;
