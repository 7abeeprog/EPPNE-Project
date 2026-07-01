// store/student-store.ts
import { create } from 'zustand';

interface StudentUIState {
  selectedCourseId: number | null;
  setSelectedCourseId: (id: number | null) => void;
}

export const useStudentUIStore = create<StudentUIState>((set) => ({
  selectedCourseId: null,
  setSelectedCourseId: (id) => set({ selectedCourseId: id }),
}));