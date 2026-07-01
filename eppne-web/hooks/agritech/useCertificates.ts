// hooks/agritech/useCertificates.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getEntityCertificates, issueCertificate } from '@/services/agritech';

export const useEntityCertificates = (entityType: string, entityId: number) => {
  return useQuery({
    queryKey: ['agritech-certificates', entityType, entityId],
    queryFn: () => getEntityCertificates(entityType, entityId).then((res) => res.data),
    enabled: !!entityId && !!entityType,
    staleTime: 2 * 60 * 1000,
  });
};

export const useIssueCertificate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof issueCertificate>[0]) => issueCertificate(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['agritech-certificates', variables.certified_entity_type, variables.certified_entity_id],
      });
    },
  });
};