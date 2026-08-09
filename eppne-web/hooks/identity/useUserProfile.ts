// hooks/identity/useUserProfile.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMe } from "./useAuth";
import { AuthService } from "@/services/auth.service";
import { useAuthStore } from "@/store/auth-store";
import { toast } from "sonner";
import type { components } from "@/src/lib/api-types";

type UserUpdate = components['schemas']['UserUpdate'];

export const useUserProfile = () => useMe();

export const useUpdateProfile = () => {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((state) => state.setUser);

  return useMutation({
    mutationFn: (data: UserUpdate) => AuthService.updateProfile(data),
    onSuccess: (data) => {
      setUser(data);
      queryClient.setQueryData(["identity", "me"], data);
      toast.success("تم تحديث الملف الشخصي بنجاح");
    },
    onError: (error: any) => {
      toast.error(error.message || "فشل تحديث الملف الشخصي");
    },
  });
};
