// hooks/invitations/useChatWithAI.ts
import { useMutation } from '@tanstack/react-query';
import { InvitationsService } from '@/services/invitations';

export const useChatWithAI = () => {
  return useMutation({
    mutationFn: ({ invitationId, data, idempotencyKey }: { invitationId: number; data: { message: string; visitor_session_id?: string }; idempotencyKey?: string }) =>
      InvitationsService.chatWithAI(invitationId, data, { 'Idempotency-Key': idempotencyKey }),
  });
};