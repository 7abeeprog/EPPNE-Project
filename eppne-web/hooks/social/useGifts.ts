// hooks/social/useGifts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getDigitalGifts, getPhysicalGifts } from '@/services/social';
import { SocialService } from '@/services/social';

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
      data: Parameters<typeof SocialService.sendDigitalGift>[0];
      idempotencyKey?: string;
    }) => SocialService.sendDigitalGift(data),
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
      data: Parameters<typeof SocialService.requestPhysicalGift>[0];
      idempotencyKey?: string;
    }) => SocialService.requestPhysicalGift(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-physical-gifts'] });
    },
  });
};