// components/social/ContractCard.tsx
'use client';

import { useState } from 'react';
import { useSignContract } from '@/hooks/social/useContracts';
import { FileText, Users, CheckCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { v4 as uuidv4 } from 'uuid';
import type { SocialSmartContract } from '@/types/social';

interface ContractCardProps {
  contract: SocialSmartContract;
}

const statusColors = {
  DRAFT: 'border-gray-500/30 text-gray-400',
  SIGNED: 'border-blue-500/30 text-blue-500',
  EXECUTED: 'border-emerald-500/30 text-emerald-500',
  TERMINATED: 'border-red-500/30 text-red-500',
};

export default function ContractCard({ contract }: ContractCardProps) {
  const [signatureHash, setSignatureHash] = useState('');
  const signContract = useSignContract();

  const handleSign = () => {
    const idempotencyKey = `sign-${contract.id}-${uuidv4()}`;
    signContract.mutate({
      contractId: contract.id,
      data: { digital_signature_hash: signatureHash || `sig-${Date.now()}` },
      idempotencyKey,
    });
  };

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{contract.title}</h4>
          <p className="text-sm text-muted-foreground/60">{contract.contract_type}</p>
          <span className={cn("text-xs px-2 py-0.5 rounded-full border", statusColors[contract.status as keyof typeof statusColors] || 'border-white/10')}>
            {contract.status}
          </span>
        </div>
        <FileText className="w-5 h-5 text-primary/60" />
      </div>

      {contract.status === 'DRAFT' && (
        <div className="mt-3 flex gap-2">
          <input
            type="text"
            value={signatureHash}
            onChange={(e) => setSignatureHash(e.target.value)}
            placeholder="توقيع رقمي (اختياري)"
            className="flex-1 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-xs"
          />
          <button
            onClick={handleSign}
            disabled={signContract.isPending}
            className="px-3 py-1.5 rounded-xl bg-primary text-primary-foreground text-xs font-medium disabled:opacity-50 flex items-center gap-1"
          >
            {signContract.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle className="w-3 h-3" />}
            توقيع
          </button>
        </div>
      )}

      {contract.signers && contract.signers.length > 0 && (
        <div className="mt-2 text-xs text-muted-foreground/50 flex items-center gap-1">
          <Users className="w-3 h-3" />
          تم التوقيع بواسطة {contract.signers.length} شخص
        </div>
      )}
    </div>
  );
}