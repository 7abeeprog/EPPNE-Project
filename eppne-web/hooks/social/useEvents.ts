// hooks/social/useEvents.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getEvents, getEvent, createEvent, attendEvent, unattendEvent } from '@/services/social';

export const useEvents = (params?: { event_type?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['social-events', params],
    queryFn: () => getEvents(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useEvent = (id: number) => {
  return useQuery({
    queryKey: ['social-event', id],
    queryFn: () => getEvent(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateEvent = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createEvent>[0]) => createEvent(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-events'] });
    },
  });
};

export const useAttendEvent = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: number) => attendEvent(eventId),
    onSuccess: (_, eventId) => {
      queryClient.invalidateQueries({ queryKey: ['social-event', eventId] });
      queryClient.invalidateQueries({ queryKey: ['social-events'] });
    },
  });
};

export const useUnattendEvent = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: number) => unattendEvent(eventId),
    onSuccess: (_, eventId) => {
      queryClient.invalidateQueries({ queryKey: ['social-event', eventId] });
      queryClient.invalidateQueries({ queryKey: ['social-events'] });
    },
  });
};