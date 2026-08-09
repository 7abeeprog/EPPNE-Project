// app/(dashboard)/ai-agents/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useAgentStore } from '@/store/agentStore';
import { useCurrentUser } from '@/hooks/identity/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Plus, Loader2, Bot, Activity, Power, PowerOff, Shield, Wallet, FileSignature } from 'lucide-react';

const agentRoles = [
  { value: 'CEO', label: 'المدير التنفيذي (CEO)' },
  { value: 'SWARM_ORCHESTRATOR', label: 'منظم السرب' },
  { value: 'CLIMATE_BROKER', label: 'وسيط المناخ' },
  { value: 'ARBITRATOR', label: 'محكم' },
  { value: 'SURVIVAL_CRISIS', label: 'أزمات البقاء' },
  { value: 'PHILANTHROPY', label: 'عمل خيري' },
  { value: 'SALES_NEGOTIATOR', label: 'مفاوض مبيعات' },
  { value: 'DEVOPS_ARCHITECT', label: 'مهندس DevOps' },
  { value: 'IOT_CONTROLLER', label: 'التحكم في IoT' },
  { value: 'HEALTH_BIO', label: 'الصحة الحيوية' },
  { value: 'ACCESSIBILITY', label: 'إمكانية الوصول' },
  { value: 'EDUCATOR', label: 'معلم' },
  { value: 'DIGITAL_TWIN', label: 'التوأم الرقمي' },
  { value: 'SUPPORT', label: 'دعم' },
];

export default function AIAgentsPage() {
  const user = useCurrentUser();
  const { agents, isLoading, fetchAgents, createAgent, updateAgentStatus, executeAgentAction } = useAgentStore();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // نموذج إنشاء وكيل
  const [newAgent, setNewAgent] = useState({
    name: '',
    role: 'SUPPORT' as any,
    system_prompt: '',
    base_model: 'gemini-1.5-pro',
    can_execute_payments: false,
    can_sign_contracts: false,
    requires_human_approval: true,
    interaction_cost_mrusdt: 0,
  });

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const handleCreateAgent = async () => {
    if (!newAgent.name.trim() || !newAgent.system_prompt.trim()) {
      toast.error('يرجى تعبئة الاسم والرسالة النظامية');
      return;
    }

    setIsSubmitting(true);
    try {
      await createAgent(newAgent);
      toast.success('تم إنشاء الوكيل بنجاح');
      setIsCreateDialogOpen(false);
      setNewAgent({
        name: '',
        role: 'SUPPORT',
        system_prompt: '',
        base_model: 'gemini-1.5-pro',
        can_execute_payments: false,
        can_sign_contracts: false,
        requires_human_approval: true,
        interaction_cost_mrusdt: 0,
      });
    } catch (error: any) {
      toast.error(error.message || 'فشل إنشاء الوكيل');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (agentId: number, currentStatus: string) => {
    const newStatus = currentStatus === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
    try {
      await updateAgentStatus(agentId, newStatus);
      toast.success(`تم ${newStatus === 'ACTIVE' ? 'تفعيل' : 'تعليق'} الوكيل بنجاح`);
    } catch (error: any) {
      toast.error(error.message || 'فشل تحديث حالة الوكيل');
    }
  };

  const handleExecuteAction = async (agentId: number, actionType: string) => {
    try {
      // مثال: تنفيذ تحليل مالي (سيتم ربطه لاحقاً)
      const result = await executeAgentAction(agentId, actionType, {
        task: 'تحليل الوضع المالي الحالي',
        timestamp: new Date().toISOString(),
      });
      toast.success('تم تنفيذ الإجراء بنجاح');
      console.log('Agent result:', result);
    } catch (error: any) {
      toast.error(error.message || 'فشل تنفيذ الإجراء');
    }
  };

  return (
    <div className="container mx-auto py-8 max-w-6xl">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Bot className="h-6 w-6" />
            وكلاء الذكاء الاصطناعي
          </h1>
          <p className="text-muted-foreground text-sm">إدارة الوكلاء الذكيين الذين يتفاعلون مع مختلف القطاعات</p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              وكيل جديد
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle>إنشاء وكيل ذكاء اصطناعي جديد</DialogTitle>
              <DialogDescription>
                حدد دور الوكيل وقدراته، وسيتم تفعيله فوراً.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="agent-name">اسم الوكيل *</Label>
                  <Input
                    id="agent-name"
                    placeholder="مثال: المستشار المالي"
                    value={newAgent.name}
                    onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agent-role">الدور *</Label>
                  <Select
                    value={newAgent.role}
                    onValueChange={(value) => setNewAgent({ ...newAgent, role: value as any })}
                  >
                    <SelectTrigger id="agent-role">
                      <SelectValue placeholder="اختر الدور" />
                    </SelectTrigger>
                    <SelectContent>
                      {agentRoles.map((role) => (
                        <SelectItem key={role.value} value={role.value}>
                          {role.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="system-prompt">الرسالة النظامية *</Label>
                <Textarea
                  id="system-prompt"
                  placeholder="حدد شخصية الوكيل، معرفته، وسلوكه..."
                  rows={4}
                  value={newAgent.system_prompt}
                  onChange={(e) => setNewAgent({ ...newAgent, system_prompt: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="base-model">النموذج الأساسي</Label>
                  <Select
                    value={newAgent.base_model}
                    onValueChange={(value) => setNewAgent({ ...newAgent, base_model: value })}
                  >
                    <SelectTrigger id="base-model">
                      <SelectValue placeholder="اختر النموذج" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="gemini-1.5-pro">Gemini 1.5 Pro</SelectItem>
                      <SelectItem value="gemini-2.0-flash">Gemini 2.0 Flash</SelectItem>
                      <SelectItem value="claude-3.5-sonnet">Claude 3.5 Sonnet</SelectItem>
                      <SelectItem value="claude-3.5-haiku">Claude 3.5 Haiku</SelectItem>
                      <SelectItem value="gpt-4.1">GPT-4.1</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="interaction-cost">تكلفة التفاعل (MR_USDT)</Label>
                  <Input
                    id="interaction-cost"
                    type="number"
                    step="0.01"
                    min="0"
                    value={newAgent.interaction_cost_mrusdt}
                    onChange={(e) => setNewAgent({ ...newAgent, interaction_cost_mrusdt: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>

              <div className="space-y-3 border rounded-lg p-4 bg-muted/30">
                <p className="font-medium text-sm">الصلاحيات</p>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">تنفيذ مدفوعات</p>
                    <p className="text-xs text-muted-foreground">يمكن للوكيل تحويل الأموال</p>
                  </div>
                  <Switch
                    checked={newAgent.can_execute_payments}
                    onCheckedChange={(checked) => setNewAgent({ ...newAgent, can_execute_payments: checked })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">توقيع عقود</p>
                    <p className="text-xs text-muted-foreground">يمكن للوكيل التوقيع رقمياً</p>
                  </div>
                  <Switch
                    checked={newAgent.can_sign_contracts}
                    onCheckedChange={(checked) => setNewAgent({ ...newAgent, can_sign_contracts: checked })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">يتطلب موافقة بشرية</p>
                    <p className="text-xs text-muted-foreground">يتم تعليق الإجراءات حتى موافقة مشرف</p>
                  </div>
                  <Switch
                    checked={newAgent.requires_human_approval}
                    onCheckedChange={(checked) => setNewAgent({ ...newAgent, requires_human_approval: checked })}
                  />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>إلغاء</Button>
              <Button onClick={handleCreateAgent} disabled={isSubmitting}>
                {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                إنشاء الوكيل
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* قائمة الوكلاء */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : agents.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Bot className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
            <p>لا يوجد وكلاء بعد</p>
            <p className="text-sm">أنشئ أول وكيل ذكاء اصطناعي لبدء الأتمتة الذكية</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <Card key={agent.id} className="relative">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Bot className="h-4 w-4" />
                      {agent.name}
                    </CardTitle>
                    <CardDescription className="text-xs">
                      {agentRoles.find(r => r.value === agent.role)?.label || agent.role}
                    </CardDescription>
                  </div>
                  <Badge variant={agent.status === 'ACTIVE' ? 'default' : agent.status === 'SUSPENDED' ? 'destructive' : 'secondary'}>
                    {agent.status === 'ACTIVE' ? 'نشط' : agent.status === 'SUSPENDED' ? 'معلق' : agent.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p className="line-clamp-2 text-muted-foreground">{agent.system_prompt}</p>
                <div className="flex flex-wrap gap-1 mt-2">
                  <Badge variant="outline" className="text-xs">
                    <Wallet className="h-3 w-3 mr-1" />
                    {agent.can_execute_payments ? '💳 مدفوعات' : '🔒'}
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    <FileSignature className="h-3 w-3 mr-1" />
                    {agent.can_sign_contracts ? '✍️ عقود' : '🔒'}
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    <Shield className="h-3 w-3 mr-1" />
                    {agent.requires_human_approval ? '👤 موافقة مطلوبة' : '🤖 تلقائي'}
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground">
                  التكلفة: {agent.interaction_cost_mrusdt || 0} MR_USDT
                </div>
              </CardContent>
              <CardFooter className="flex justify-between gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleToggleStatus(agent.id, agent.status)}
                >
                  {agent.status === 'ACTIVE' ? (
                    <><PowerOff className="h-3 w-3 mr-1" /> تعليق</>
                  ) : (
                    <><Power className="h-3 w-3 mr-1" /> تفعيل</>
                  )}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleExecuteAction(agent.id, 'ANALYZE_FINANCE')}
                  disabled={agent.status !== 'ACTIVE'}
                >
                  <Activity className="h-3 w-3 mr-1" />
                  تحليل
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}