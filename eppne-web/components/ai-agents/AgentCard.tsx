// components/ai-agents/AgentCard.tsx
'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';
import { Brain, Zap, Shield, Wallet, FileText, Power, PowerOff } from 'lucide-react';
import type { AIAgent } from '@/types/ai-agents';
import { AGENT_ROLE_LABELS, AGENT_STATUS_CONFIG } from '@/types/ai-agents';

interface AgentCardProps {
  agent: AIAgent;
  className?: string;
}

export default function AgentCard({ agent, className }: AgentCardProps) {
  const roleInfo = AGENT_ROLE_LABELS[agent.role] || { label: agent.role, icon: '🤖', description: '' };
  const statusInfo = AGENT_STATUS_CONFIG[agent.status] || AGENT_STATUS_CONFIG.IDLE;

  return (
    <Link
      href={`/ai-agents/${agent.id}`}
      className={cn(
        "group block p-5 rounded-2xl transition-all duration-300",
        "bg-card/30 backdrop-blur-xl border border-white/10",
        "hover:bg-card/50 hover:border-primary/30",
        agent.status === 'ACTIVE' 
          ? "hover:shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.2)]" 
          : "hover:shadow-none",
        className
      )}
    >
      <div className="flex items-start gap-4">
        {/* أيقونة الدور */}
        <div className={cn(
          "flex-shrink-0 w-12 h-12 rounded-2xl flex items-center justify-center text-2xl transition-all duration-300",
          agent.status === 'ACTIVE' 
            ? "bg-primary/20 shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)]" 
            : "bg-white/5"
        )}>
          {roleInfo.icon}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-semibold text-foreground/90 truncate group-hover:text-primary transition-colors">
              {agent.name}
            </h3>
            <span className={cn(
              "text-xs px-2.5 py-1 rounded-full border backdrop-blur-sm transition-all",
              statusInfo.color,
              agent.status === 'ACTIVE' && "animate-pulse"
            )}>
              {statusInfo.label}
            </span>
          </div>
          
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-muted-foreground/50">{roleInfo.label}</span>
            <span className="w-1 h-1 rounded-full bg-muted-foreground/20" />
            <span className="text-xs text-muted-foreground/40">{agent.base_model}</span>
          </div>

          {/* الصلاحيات */}
          <div className="flex items-center gap-3 mt-2">
            {agent.can_execute_payments && (
              <span className="flex items-center gap-1 text-[10px] text-amber-500/70 bg-amber-500/10 px-2 py-0.5 rounded-full">
                <Wallet className="w-3 h-3" />
                دفع
              </span>
            )}
            {agent.can_sign_contracts && (
              <span className="flex items-center gap-1 text-[10px] text-blue-500/70 bg-blue-500/10 px-2 py-0.5 rounded-full">
                <FileText className="w-3 h-3" />
                توقيع
              </span>
            )}
            {agent.requires_human_approval && (
              <span className="flex items-center gap-1 text-[10px] text-purple-500/70 bg-purple-500/10 px-2 py-0.5 rounded-full">
                <Shield className="w-3 h-3" />
                موافقة بشرية
              </span>
            )}
          </div>
        </div>

        {/* حالة النشاط */}
        <div className="flex-shrink-0">
          {agent.status === 'ACTIVE' ? (
            <div className="p-2 rounded-xl bg-emerald-500/20 text-emerald-500">
              <Power className="w-4 h-4" />
            </div>
          ) : (
            <div className="p-2 rounded-xl bg-gray-500/10 text-gray-500">
              <PowerOff className="w-4 h-4" />
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}