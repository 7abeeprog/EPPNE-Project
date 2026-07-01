// hooks/social/useGifts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getDigitalGifts, getPhysicalGifts, sendDigitalGift, requestPhysicalGift } from '@/services/social';

export const useDigitalGifts = () => {
  return useQuery({
    queryKey: ['social-digital-gifts'],
    queryFn: () => getDigitalGifts().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const usePhysicalGifts = () => {
  return useQuery({
    queryKey: ['social-physical-gifts'],
    queryFn: () => getPhysicalGifts().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useSendDigitalGift = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      data,
      idempotencyKey,
    }: {
      data: Parameters<typeof sendDigitalGift>[0];
      idempotencyKey?: string;
    }) => sendDigitalGift(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-digital-gifts'] });
    },
  });
};

export const useRequestPhysicalGift = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      data,
      idempotencyKey,
    }: {
      data: Parameters<typeof requestPhysicalGift>[0];
      idempotencyKey?: string;
    }) => requestPhysicalGift(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-physical-gifts'] });
    },
  });
};