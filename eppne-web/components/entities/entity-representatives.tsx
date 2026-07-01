// components/entities/entity-representatives.tsx
"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { EntityRole } from "@/types/entity";
import { Trash2, UserPlus, ShieldAlert, PenTool, Users, Search, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

// 🟢 استدعاء الهوك السيادي لقراءة البيانات
import { useEntityDetails } from "@/hooks/use-entities";

interface EntityRepresentativesProps {
  entityId: number;
}

const roleLabels: Record<EntityRole, string> = {
  OWNER: "المالك السيادي",
  EXECUTIVE_DIRECTOR: "المدير التنفيذي",
  SIGNATORY: "مفوض بالتوقيع",
  REPRESENTATIVE: "ممثل إداري",
};

// 🟢 شارات نيون لتوضيح الأدوار
const roleStyles: Record<EntityRole, string> = {
  OWNER: "bg-purple-500/10 border-purple-500/30 text-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.2)]",
  EXECUTIVE_DIRECTOR: "bg-blue-500/10 border-blue-500/30 text-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.2)]",
  SIGNATORY: "bg-emerald-500/10 border-emerald-500/30 text-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.2)]",
  REPRESENTATIVE: "bg-slate-500/10 border-slate-500/30 text-slate-400",
};

export function EntityRepresentatives({ entityId }: EntityRepresentativesProps) {
  const queryClient = useQueryClient();
  
  // 🟢 1. جلب البيانات تلقائياً بفضل TanStack (بدون useEffect)
  const { representatives = [], isLoading: isRepsLoading } = useEntityDetails(entityId);

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [selectedRole, setSelectedRole] = useState<EntityRole>(EntityRole.REPRESENTATIVE);
  const [canSign, setCanSign] = useState(false);
  const [searchEmail, setSearchEmail] = useState("");

  // 🟢 2. محرك البحث عن المستخدمين
  const { data: searchResults, refetch: searchUsers, isFetching: isSearching } = useQuery({
    queryKey: ["user-search", searchEmail],
    queryFn: async () => {
      if (!searchEmail || searchEmail.length < 3) return [];
      const res = await apiClient.get(`/users/search?q=${searchEmail}`);
      return res.data;
    },
    enabled: false,
  });

  const handleSearch = () => {
    if (searchEmail.length >= 3) searchUsers();
  };

  // 🟢 3. محركات التعديل (Mutations)
  const addRepMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await apiClient.post(`/sovereign-entities/${entityId}/representatives`, data);
      return response.data;
    },
    onSuccess: () => {
      toast.success("تم تشفير صلاحيات الممثل وإضافته بنجاح! 🛡️");
      queryClient.invalidateQueries({ queryKey: ['entities', 'representatives', entityId] });
      setIsDialogOpen(false);
      setSelectedUserId("");
      setSelectedRole(EntityRole.REPRESENTATIVE);
      setCanSign(false);
      setSearchEmail("");
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "فشل تفويض الممثل الجديد.");
    }
  });

  const removeRepMutation = useMutation({
    mutationFn: async (userId: number) => {
      await apiClient.delete(`/sovereign-entities/${entityId}/representatives/${userId}`);
    },
    onSuccess: () => {
      toast.success("تم سحب الصلاحيات وإزالة الممثل بنجاح.");
      queryClient.invalidateQueries({ queryKey: ['entities', 'representatives', entityId] });
    },
    onError: () => toast.error("فشلت عملية سحب الصلاحيات.")
  });

  const handleAddRepresentative = () => {
    if (!selectedUserId) {
      toast.error("يرجى تحديد المستخدم لتفويضه.");
      return;
    }
    addRepMutation.mutate({
      user_id: parseInt(selectedUserId),
      role: selectedRole,
      can_sign_contracts: canSign,
    });
  };

  const handleRemove = (userId: number) => {
    if (confirm("تحذير سيادي: هل أنت متأكد من سحب كافة الصلاحيات وإزالة هذا الممثل؟")) {
      removeRepMutation.mutate(userId);
    }
  };

  return (
    <div className="w-full rounded-[2rem] border border-white/10 bg-card/30 backdrop-blur-xl shadow-lg relative overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* إضاءة خلفية نيون */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 blur-[80px] rounded-full pointer-events-none opacity-50" />

      {/* 🟢 الرأس السيادي */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 md:p-8 border-b border-white/5 bg-background/20 relative z-10">
        <div>
          <h2 className="text-2xl font-black flex items-center gap-3 text-foreground">
            <div className="p-2.5 bg-primary/10 rounded-xl border border-primary/20 shadow-inner">
              <Users className="h-6 w-6 text-primary" />
            </div>
            مجلس الإدارة والممثلين
          </h2>
          <p className="mt-2 text-sm text-muted-foreground font-medium">
            الأشخاص المفوضون سيادياً بإدارة الكيان وإبرام العقود الذكية
          </p>
        </div>

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="font-bold rounded-xl shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:scale-105 transition-all">
              <UserPlus className="ml-2 h-5 w-5" />
              تفويض ممثل جديد
            </Button>
          </DialogTrigger>
          
          {/* 🟢 نافذة إضافة ممثل زجاجية */}
          <DialogContent className="sm:max-w-[500px] bg-background/80 backdrop-blur-2xl border-white/10 shadow-[0_0_50px_rgba(var(--primary-rgb),0.15)] rounded-[2rem] p-6">
            <DialogHeader>
              <DialogTitle className="text-xl font-black text-foreground flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-primary" /> تفويض ممثل سيادي
              </DialogTitle>
              <DialogDescription className="font-medium text-muted-foreground">
                ابحث عن المستخدم وقم بتشفير صلاحياته داخل الكيان.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-6 py-4">
              
              {/* البحث */}
              <div className="space-y-3">
                <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">البحث عن مستخدم (البريد أو الاسم)</Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="example@email.com"
                      value={searchEmail}
                      onChange={(e) => setSearchEmail(e.target.value)}
                      className="pl-3 pr-9 h-12 bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl"
                    />
                  </div>
                  <Button type="button" onClick={handleSearch} disabled={isSearching} className="h-12 rounded-xl px-6 font-bold">
                    {isSearching ? <Loader2 className="h-4 w-4 animate-spin" /> : "بحث"}
                  </Button>
                </div>
              </div>

              {/* نتائج البحث */}
              {searchResults && searchResults.length > 0 && (
                <div className="space-y-3 p-4 bg-primary/5 rounded-2xl border border-primary/10">
                  <Label className="text-xs font-bold uppercase tracking-wider text-primary">المستخدم المستهدف</Label>
                  <Select onValueChange={setSelectedUserId}>
                    <SelectTrigger className="h-12 bg-background/80 border-white/10 focus:ring-primary rounded-xl font-bold">
                      <SelectValue placeholder="-- اختر المستخدم من النتائج --" />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl border-white/10 backdrop-blur-2xl bg-card/90">
                      {searchResults.map((user: any) => (
                        <SelectItem key={user.id} value={user.id.toString()} className="font-medium">
                          {user.name_ar || user.username} <span className="text-muted-foreground/50 ml-2">({user.email})</span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* الدور والصلاحيات */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-3">
                  <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">الدور الإداري</Label>
                  <Select onValueChange={(v) => setSelectedRole(v as EntityRole)} defaultValue={EntityRole.REPRESENTATIVE}>
                    <SelectTrigger className="h-12 bg-background/50 border-white/10 focus:ring-primary rounded-xl font-bold">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl border-white/10 backdrop-blur-2xl bg-card/90">
                      {Object.entries(roleLabels).map(([value, label]) => (
                        <SelectItem key={value} value={value} className="font-bold">{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-3 flex flex-col justify-end">
                  <div className={`flex items-center justify-between p-3.5 rounded-xl border transition-colors ${canSign ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-background/50 border-white/10'}`}>
                    <Label className={`text-xs font-bold uppercase tracking-wider cursor-pointer ${canSign ? 'text-emerald-500' : 'text-muted-foreground'}`}>
                      صلاحية التوقيع
                    </Label>
                    <Switch checked={canSign} onCheckedChange={setCanSign} />
                  </div>
                </div>
              </div>

            </div>
            <DialogFooter className="gap-2 sm:gap-0 mt-4 border-t border-border/50 pt-4">
              <Button variant="ghost" onClick={() => setIsDialogOpen(false)} className="rounded-xl hover:bg-destructive/10 hover:text-destructive font-bold">إلغاء الأمر</Button>
              <Button onClick={handleAddRepresentative} disabled={addRepMutation.isPending} className="rounded-xl font-bold shadow-lg px-8">
                {addRepMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <ShieldAlert className="h-4 w-4 mr-2" />}
                اعتماد التفويض
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* 🟢 محتوى الجدول الزجاجي */}
      <div className="p-0 md:p-4 relative z-10">
        <div className="rounded-2xl border border-white/5 bg-background/30 overflow-hidden shadow-inner">
          <Table>
            <TableHeader className="bg-background/40">
              <TableRow className="border-white/5 hover:bg-transparent">
                <TableHead className="font-bold text-muted-foreground">الكود التعريفي (ID)</TableHead>
                <TableHead className="font-bold text-muted-foreground">الدور السيادي</TableHead>
                <TableHead className="font-bold text-muted-foreground text-center">توقيع العقود</TableHead>
                <TableHead className="font-bold text-muted-foreground">تاريخ التفويض</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isRepsLoading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-12">
                    <Loader2 className="h-8 w-8 mx-auto mb-3 text-primary/40 animate-spin" />
                    <p className="text-sm font-bold text-muted-foreground">جاري تحميل السجل السيادي للممثلين...</p>
                  </TableCell>
                </TableRow>
              ) : representatives.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-16">
                    <Users className="h-10 w-10 mx-auto mb-4 text-muted-foreground/30" />
                    <p className="text-lg font-black text-foreground/70 mb-1">لا يوجد ممثلون مفوضون</p>
                    <p className="text-sm text-muted-foreground font-medium">الكيان يفتقر للإدارة حالياً</p>
                  </TableCell>
                </TableRow>
              ) : (
                representatives.map((rep: any) => (
                  <TableRow key={rep.id} className="border-white/5 hover:bg-primary/5 transition-colors">
                    <TableCell className="font-mono font-bold text-muted-foreground">
                      #{rep.user_id}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={`${roleStyles[rep.role as EntityRole] || roleStyles.REPRESENTATIVE} backdrop-blur-md px-3 py-1 rounded-lg border`}>
                        <span className="font-bold tracking-wide">{roleLabels[rep.role as EntityRole] || "غير معروف"}</span>
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      {rep.can_sign_contracts ? (
                        <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/30 px-3 py-1">
                          <PenTool className="h-3 w-3 ml-1" /> مفوض
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="bg-background/50 text-muted-foreground border-white/10 px-3 py-1">
                          غير مفوض
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-sm text-muted-foreground">
                      {new Date(rep.created_at).toLocaleDateString("ar-EG")}
                    </TableCell>
                    <TableCell className="text-left">
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        onClick={() => handleRemove(rep.user_id)}
                        disabled={removeRepMutation.isPending}
                        className="h-8 w-8 hover:bg-red-500/20 hover:text-red-500 rounded-lg transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}