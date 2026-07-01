// store/socialStore.ts
import { create } from 'zustand';
import type { Post, SocialGroup, UserOccasion, DigitalGift } from '@/types/social';

interface SocialState {
  selectedPost: Post | null;
  selectedGroup: SocialGroup | null;
  selectedOccasion: UserOccasion | null;
  composerOpen: boolean;
  notifications: number;
  setSelectedPost: (post: Post | null) => void;
  setSelectedGroup: (group: SocialGroup | null) => void;
  setSelectedOccasion: (occasion: UserOccasion | null) => void;
  setComposerOpen: (open: boolean) => void;
  setNotifications: (count: number) => void;
  incrementNotifications: () => void;
  clearNotifications: () => void;
}

export const useSocialStore = create<SocialState>((set) => ({
  selectedPost: null,
  selectedGroup: null,
  selectedOccasion: null,
  composerOpen: false,
  notifications: 0,

  setSelectedPost: (post) => set({ selectedPost: post }),
  setSelectedGroup: (group) => set({ selectedGroup: group }),
  setSelectedOccasion: (occasion) => set({ selectedOccasion: occasion }),
  setComposerOpen: (open) => set({ composerOpen: open }),
  setNotifications: (count) => set({ notifications: count }),
  incrementNotifications: () => set((state) => ({ notifications: state.notifications + 1 })),
  clearNotifications: () => set({ notifications: 0 }),
}));