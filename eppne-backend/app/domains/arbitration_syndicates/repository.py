from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from typing import Optional, List
from app.domains.arbitration_syndicates.models import *
from app.core.errors import NotFoundError

class ArbitrationSyndicatesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Arbitration ----------
    async def create_case(self, **kwargs) -> ArbitrationCase:
        case = ArbitrationCase(**kwargs)
        self.db.add(case)
        await self.db.commit()
        await self.db.refresh(case)
        return case

    async def get_case(self, case_id: int) -> Optional[ArbitrationCase]:
        result = await self.db.execute(select(ArbitrationCase).where(ArbitrationCase.id == case_id))
        return result.scalar_one_or_none()

    async def list_user_cases(self, user_id: int):
        result = await self.db.execute(
            select(ArbitrationCase).where(
                (ArbitrationCase.claimant_id == user_id) | (ArbitrationCase.respondent_id == user_id)
            ).order_by(ArbitrationCase.created_at.desc())
        )
        return result.scalars().all()

    async def update_case_status(self, case_id: int, status: str, verdict: str = None, tx_hash: str = None) -> ArbitrationCase:
        values = {"status": status}
        if verdict:
            values["final_verdict"] = verdict
        if tx_hash:
            values["enforcement_tx_hash"] = tx_hash
        await self.db.execute(update(ArbitrationCase).where(ArbitrationCase.id == case_id).values(**values))
        await self.db.commit()
        return await self.get_case(case_id)

    async def create_jury_vote(self, **kwargs) -> CrowdJury:
        vote = CrowdJury(**kwargs)
        self.db.add(vote)
        await self.db.commit()
        await self.db.refresh(vote)
        return vote

    async def get_jury_votes_for_case(self, case_id: int) -> List[CrowdJury]:
        result = await self.db.execute(select(CrowdJury).where(CrowdJury.case_id == case_id))
        return result.scalars().all()

    # ---------- Syndicates ----------
    async def create_syndicate(self, **kwargs) -> SovereignSyndicate:
        synd = SovereignSyndicate(**kwargs)
        self.db.add(synd)
        await self.db.commit()
        await self.db.refresh(synd)
        return synd

    async def get_syndicate(self, syndicate_id: int) -> Optional[SovereignSyndicate]:
        result = await self.db.execute(select(SovereignSyndicate).where(SovereignSyndicate.id == syndicate_id))
        return result.scalar_one_or_none()

    async def list_syndicates(self, tenant_id: int):
        result = await self.db.execute(select(SovereignSyndicate).where(SovereignSyndicate.tenant_id == tenant_id, SovereignSyndicate.is_active == True))
        return result.scalars().all()

    async def create_membership(self, **kwargs) -> SyndicateMembership:
        membership = SyndicateMembership(**kwargs)
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def get_membership(self, user_id: int, syndicate_id: int) -> Optional[SyndicateMembership]:
        result = await self.db.execute(
            select(SyndicateMembership).where(
                SyndicateMembership.member_user_id == user_id,
                SyndicateMembership.syndicate_id == syndicate_id,
                SyndicateMembership.status == "ACTIVE"
            )
        )
        return result.scalar_one_or_none()

    async def create_license(self, **kwargs) -> ProfessionalLicense:
        license = ProfessionalLicense(**kwargs)
        self.db.add(license)
        await self.db.commit()
        await self.db.refresh(license)
        return license

    async def get_licenses_for_user(self, user_id: int) -> List[ProfessionalLicense]:
        result = await self.db.execute(select(ProfessionalLicense).where(ProfessionalLicense.user_id == user_id))
        return result.scalars().all()

    # ---------- Elections ----------
    async def create_election(self, **kwargs) -> SyndicateElection:
        election = SyndicateElection(**kwargs)
        self.db.add(election)
        await self.db.commit()
        await self.db.refresh(election)
        return election

    async def get_election(self, election_id: int) -> Optional[SyndicateElection]:
        result = await self.db.execute(select(SyndicateElection).where(SyndicateElection.id == election_id))
        return result.scalar_one_or_none()

    async def create_candidate(self, **kwargs) -> ElectionCandidate:
        candidate = ElectionCandidate(**kwargs)
        self.db.add(candidate)
        await self.db.commit()
        await self.db.refresh(candidate)
        return candidate

    async def list_candidates(self, election_id: int) -> List[ElectionCandidate]:
        result = await self.db.execute(select(ElectionCandidate).where(ElectionCandidate.election_id == election_id))
        return result.scalars().all()

    async def create_vote(self, **kwargs) -> ElectionVote:
        vote = ElectionVote(**kwargs)
        self.db.add(vote)
        await self.db.commit()
        await self.db.refresh(vote)
        return vote

    async def has_voted(self, election_id: int, voter_id: int) -> bool:
        result = await self.db.execute(
            select(ElectionVote).where(
                ElectionVote.election_id == election_id,
                ElectionVote.voter_user_id == voter_id
            )
        )
        return result.scalar_one_or_none() is not None