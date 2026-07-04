# app/domains/finance/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from decimal import Decimal
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.domains.finance.schemas import (
    TransferRequest, TransferResponse, SwapRequest, SwapResponse, 
    WalletBalanceResponse, TransactionResponse, CryptoModeToggle, 
    ExchangeRatesUpdate, MintRequest, PaginatedTransactionResponse, MaxSupplyUpdate
)
from app.domains.finance.service import FinanceService
from app.api.deps import get_current_active_user, get_current_superuser, require_roles
from app.domains.identity.models import User
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/finance", tags=["Sovereign Finance"])


# ==========================================
# 1. المستخدم العادي
# ==========================================

@router.get("/balances", response_model=WalletBalanceResponse)
@rate_limit(max_requests=60, window_seconds=60)
async def get_balances(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = FinanceService(db)
    state = await service.state_repo.get_state()
    hide_crypto = (state.crypto_mode == "POINTS_ONLY")
    balances = await service.get_balances(current_user.id, hide_crypto=hide_crypto)
    return {"balances": balances}


@router.post("/transfer", response_model=TransferResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def transfer_funds(
    req: TransferRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = FinanceService(db)
    
    # 🔥 إضافة Idempotency Key لتجنب التكرار
    idempotency_key = req.idempotency_key or f"transfer-{uuid.uuid4().hex[:16]}"
    
    tx = await service.transfer(
        sender_id=current_user.id,
        receiver_email=req.receiver_email,
        currency=req.currency,
        amount=req.amount,
        notes=req.notes,
        idempotency_key=idempotency_key,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    return TransferResponse(
        tx_hash=tx.tx_hash,
        amount=float(tx.amount),
        currency=tx.currency,
        status=tx.status,
        created_at=tx.created_at
    )


@router.post("/swap", response_model=SwapResponse)
@rate_limit(max_requests=15, window_seconds=60)
async def swap_currencies(
    req: SwapRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = FinanceService(db)
    
    # 🔥 إضافة Idempotency Key
    idempotency_key = req.idempotency_key or f"swap-{uuid.uuid4().hex[:16]}"
    
    result = await service.swap(
        user_id=current_user.id,
        from_currency=req.from_currency,
        to_currency=req.to_currency,
        amount_in=req.amount_in,
        idempotency_key=idempotency_key,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    return SwapResponse(**result)


@router.get("/history", response_model=PaginatedTransactionResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_history(
    skip: int = 0,
    limit: int = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    currency: Optional[str] = None,
    tx_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب سجل المعاملات مع Pagination و فلترة اختيارية.
    🔥 Pagination إلزامي (حد أقصى 1000 عنصر).
    """
    service = FinanceService(db)
    
    # فرض الحد الأقصى للـ limit
    safe_limit = min(limit, 1000)
    
    # جلب المعاملات
    txs = await service.get_transaction_history(
        user_id=current_user.id,
        skip=skip,
        limit=safe_limit,
        start_date=start_date,
        end_date=end_date,
        currency=currency,
        tx_type=tx_type
    )
    
    # جلب العدد الإجمالي (لـ Pagination)
    from app.domains.finance.repository import TransactionRepository
    repo = TransactionRepository(db)
    total = await repo.count_by_user(
        user_id=current_user.id,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        currency=currency,
        tx_type=tx_type
    )
    
    return PaginatedTransactionResponse(
        data=txs,
        total=total,
        skip=skip,
        limit=safe_limit
    )


# ==========================================
# 2. إدارة البنك المركزي (Super Admin Only)
# ==========================================

@router.get("/admin/crypto-mode")
async def get_crypto_mode(
    db: AsyncSession = Depends(get_db)
):
    service = FinanceService(db)
    state = await service.state_repo.get_state()
    return {"crypto_mode": state.crypto_mode, "max_supply": state.max_supply}


@router.post("/admin/crypto-mode")
async def set_crypto_mode(
    req: CryptoModeToggle,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = FinanceService(db)
    await service.state_repo.update_crypto_mode(req.mode, current_user.id)
    return {"status": "SUCCESS", "mode": req.mode}


@router.post("/admin/exchange-rates")
async def set_exchange_rates(
    req: ExchangeRatesUpdate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = FinanceService(db)
    await service.state_repo.update_exchange_rates(req.rates, current_user.id)
    return {"status": "SUCCESS", "rates": req.rates}


@router.post("/admin/mint")
async def mint_funds(
    req: MintRequest,
    request: Request,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    طباعة عملات جديدة (من البنك المركزي).
    🔥 يتطلب صلاحيات Super Admin.
    🔥 التحقق من Idempotency و Max Supply.
    """
    service = FinanceService(db)
    
    # 🔥 توليد Idempotency Key للطباعة
    idempotency_key = f"mint-{uuid.uuid4().hex[:16]}"
    
    tx = await service.mint_currency(
        admin_id=current_user.id,
        currency=req.currency,
        amount=req.amount,
        idempotency_key=idempotency_key
    )
    return {
        "status": "SUCCESS", 
        "tx_hash": tx.tx_hash, 
        "amount": req.amount, 
        "currency": req.currency
    }


@router.post("/admin/max-supply")
async def set_max_supply(
    req: MaxSupplyUpdate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    تحديث الحد الأقصى للطباعة لكل عملة.
    🔥 يتطلب صلاحيات Super Admin.
    """
    service = FinanceService(db)
    await service.state_repo.update_max_supply(req.max_supply, current_user.id)
    return {"status": "SUCCESS", "max_supply": req.max_supply}