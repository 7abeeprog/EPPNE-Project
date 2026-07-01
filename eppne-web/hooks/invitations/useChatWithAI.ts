// hooks/invitations/useChatWithAI.ts
import { useMutation } from '@tanstack/react-query';
import { chatWithAI } from '@/services/invitations';

export const useChatWithAI = () => {
  return useMutation({
    mutationFn: ({ invitationId, data, idempotencyKey }: { invitationId: number; data: { message: string; visitor_session_id?: string }; idempotencyKey?: string }) =>
      chatWithAI(invitationId, data, idempotencyKey),
  });
};