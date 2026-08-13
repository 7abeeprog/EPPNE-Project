# app/domains/tourism_sports/repository.py (الإصدار النهائي المتكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import Optional, List
from app.domains.tourism_sports.models import (
    TourismDestination, AccommodationFacility, TourismProgram,
    ProgramParticipant, EntertainmentVenue, EntertainmentEvent,
    NFTTicket, SportsOrganization, PlayerProfile,
    PlayerTransfer, Tournament, SportsMatch
)
from app.core.errors import NotFoundError


class TourismSportsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Tourism ----------
    async def create_destination(self, **kwargs) -> TourismDestination:
        dest = TourismDestination(**kwargs)
        self.db.add(dest)
        await self.db.commit()
        await self.db.refresh(dest)
        return dest

    async def list_destinations(self, tenant_id: int, dest_type: Optional[str] = None):
        query = select(TourismDestination).where(
            TourismDestination.tenant_id == tenant_id,
            TourismDestination.is_active == True
        )
        if dest_type:
            query = query.where(TourismDestination.destination_type == dest_type)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_accommodation(self, **kwargs) -> AccommodationFacility:
        acc = AccommodationFacility(**kwargs)
        self.db.add(acc)
        await self.db.commit()
        await self.db.refresh(acc)
        return acc

    async def create_program(self, **kwargs) -> TourismProgram:
        prog = TourismProgram(**kwargs)
        self.db.add(prog)
        await self.db.commit()
        await self.db.refresh(prog)
        return prog

    async def create_program_participant(self, **kwargs) -> ProgramParticipant:
        participant = ProgramParticipant(**kwargs)
        self.db.add(participant)
        await self.db.flush()
        await self.db.refresh(participant)
        return participant

    # ---------- Entertainment ----------
    async def create_venue(self, **kwargs) -> EntertainmentVenue:
        venue = EntertainmentVenue(**kwargs)
        self.db.add(venue)
        await self.db.commit()
        await self.db.refresh(venue)
        return venue

    async def create_event(self, **kwargs) -> EntertainmentEvent:
        event = EntertainmentEvent(**kwargs)
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def create_ticket(self, **kwargs) -> NFTTicket:
        ticket = NFTTicket(**kwargs)
        self.db.add(ticket)
        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket

    # ---------- Sports ----------
    async def create_sports_org(self, **kwargs) -> SportsOrganization:
        org = SportsOrganization(**kwargs)
        self.db.add(org)
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def get_sports_org(self, org_id: int, tenant_id: int) -> Optional[SportsOrganization]:
        """جلب منظمة رياضية مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(SportsOrganization).where(
                SportsOrganization.id == org_id,
                SportsOrganization.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_player_profile(self, **kwargs) -> PlayerProfile:
        player = PlayerProfile(**kwargs)
        self.db.add(player)
        await self.db.commit()
        await self.db.refresh(player)
        return player

    async def get_player_profile(self, user_id: int) -> Optional[PlayerProfile]:
        result = await self.db.execute(
            select(PlayerProfile).where(PlayerProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_transfer(self, **kwargs) -> PlayerTransfer:
        transfer = PlayerTransfer(**kwargs)
        self.db.add(transfer)
        await self.db.flush()
        await self.db.refresh(transfer)
        return transfer

    async def create_tournament(self, **kwargs) -> Tournament:
        tournament = Tournament(**kwargs)
        self.db.add(tournament)
        await self.db.commit()
        await self.db.refresh(tournament)
        return tournament

    async def create_match(self, **kwargs) -> SportsMatch:
        match = SportsMatch(**kwargs)
        self.db.add(match)
        await self.db.commit()
        await self.db.refresh(match)
        return match

    async def get_program(self, program_id: int) -> Optional[TourismProgram]:
        result = await self.db.execute(
            select(TourismProgram).where(TourismProgram.id == program_id)
        )
        return result.scalar_one_or_none()

    async def count_participants(self, program_id: int) -> int:
        result = await self.db.execute(
            select(func.count(ProgramParticipant.id)).where(
                ProgramParticipant.program_id == program_id
            )
        )
        return result.scalar_one()

    async def get_event(self, event_id: int) -> Optional[EntertainmentEvent]:
        result = await self.db.execute(
            select(EntertainmentEvent).where(EntertainmentEvent.id == event_id)
        )
        return result.scalar_one_or_none()