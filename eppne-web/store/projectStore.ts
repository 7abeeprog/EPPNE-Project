// store/projectStore.ts
import { create } from 'zustand';
import type { Project } from '@/types/projects';

interface ProjectStore {
  selectedProject: Project | null;
  selectedProjectId: number | null;
  setSelectedProject: (project: Project) => void;
  clearSelectedProject: () => void;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  selectedProject: null,
  selectedProjectId: null,
  setSelectedProject: (project) => set({ selectedProject: project, selectedProjectId: project.id }),
  clearSelectedProject: () => set({ selectedProject: null, selectedProjectId: null }),
}));