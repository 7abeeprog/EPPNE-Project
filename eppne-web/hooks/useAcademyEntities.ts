// hooks/useAcademyEntities.ts
import { useQuery } from "@tanstack/react-query";
import { AcademyService } from "@/services/academy.service";
import { OrganizationEntity, PaginatedResponse } from "@/types/academy";

export const useAcademyEntities = (
  skip: number = 0,
  limit: number = 100
) => {
  return useQuery({
    queryKey: ["academy", "entities", skip, limit],
    queryFn: async (): Promise<PaginatedResponse<OrganizationEntity>> => {
      // افترضنا وجود دالة getOrganizationEntities في AcademyService
      // إذا لم تكن موجودة، سنقوم بإنشائها الآن داخل الخدمة
      return AcademyService.getOrganizationEntities(skip, limit);
    },
    staleTime: 5 * 60 * 1000,
  });
};