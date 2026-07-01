// store/invitationsStore.ts
import { create } from 'zustand';
import type { Lead, MarketingCampaign, SupportTicket, SovereignInvitation } from '@/types/invitations';

interface InvitationsState {
  selectedLead: Lead | null;
  selectedCampaign: MarketingCampaign | null;
  selectedInvitation: SovereignInvitation | null;
  selectedTicket: SupportTicket | null;
  setSelectedLead: (lead: Lead | null) => void;
  setSelectedCampaign: (campaign: MarketingCampaign | null) => void;
  setSelectedInvitation: (invitation: SovereignInvitation | null) => void;
  setSelectedTicket: (ticket: SupportTicket | null) => void;
}

export const useInvitationsStore = create<InvitationsState>((set) => ({
  selectedLead: null,
  selectedCampaign: null,
  selectedInvitation: null,
  selectedTicket: null,
  setSelectedLead: (lead) => set({ selectedLead: lead }),
  setSelectedCampaign: (campaign) => set({ selectedCampaign: campaign }),
  setSelectedInvitation: (invitation) => set({ selectedInvitation: invitation }),
  setSelectedTicket: (ticket) => set({ selectedTicket: ticket }),
}));