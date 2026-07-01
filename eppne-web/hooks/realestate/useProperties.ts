// hooks/realestate/useProperties.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getProperties,
  getProperty,
  createProperty,
  updateProperty,
  deleteProperty,
} from '@/services/realestate';
import type { Property, PropertyFormData } from '@/types/realestate';

export const useProperties = (params?: { skip?: number; limit?: number; type?: string }) => {
  return useQuery({
    queryKey: ['realestate-properties', params],
    queryFn: () => getProperties(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useProperty = (id: number) => {
  return useQuery({
    queryKey: ['realestate-property', id],
    queryFn: () => getProperty(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateProperty = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PropertyFormData) => createProperty(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['realestate-properties'] });
    },
  });
};