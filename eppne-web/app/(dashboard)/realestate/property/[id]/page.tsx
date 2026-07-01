// app/(dashboard)/realestate/property/[id]/page.tsx
'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Image from 'next/image';
import { useProperty, useUpdateProperty } from '@/hooks/realestate/useProperties';
import { useAssetTokenization } from '@/hooks/realestate/useTokenization';
import { useBuyFractionalShare } from '@/hooks/realestate/useTokenization';
import { usePropertyOwnerships } from '@/hooks/realestate/usePropertyOwnerships';
import { format } from 'date-fns/ar';
import {
  Loader2,
  ArrowLeft,
  MapPin,
  Ruler,
  DollarSign,
  Building2,
  Users,
  Edit,
  Save,
  X,
  Shield,
  TrendingUp,
  Calendar,
  CheckCircle,
  AlertTriangle,
  ShoppingCart,
  Percent,
  Wallet,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { v4 as uuidv4 } from 'uuid';
import type { PropertyType } from '@/types/realestate';

const typeLabels: Record<PropertyType, string> = {
  APARTMENT: 'شقة',
  VILLA: 'فيلا',
  OFFICE: 'مكتب',
  RETAIL: 'متجر',
  WAREHOUSE: 'مستودع',
  FACTORY: 'مصنع',
  LAND: 'أرض',
};

const statusColors = {
  AVAILABLE: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
  SOLD: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
  RENTED: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
  UNDER_CONSTRUCTION: 'border-purple-500/30 text-purple-500 bg-purple-500/5',
};

export default function PropertyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const propertyId = parseInt(params.id as string);

  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<any>({});
  const [buyPercentage, setBuyPercentage] = useState(10);
  const [showBuyModal, setShowBuyModal] = useState(false);

  // ========== Hooks ==========
  const { data: property, isLoading: propertyLoading, refetch } = useProperty(propertyId);
  const { data: tokenization, isLoading: tokenLoading } = useAssetTokenization(propertyId);
  const { data: ownerships, isLoading: ownershipLoading } = usePropertyOwnerships(propertyId);

  const updateProperty = useUpdateProperty();
  const buyFraction = useBuyFractionalShare();

  // ========== Handlers ==========
  const handleEdit = () => {
    setIsEditing(true);
    setEditData(property);
  };

  const handleSaveEdit = () => {
    updateProperty.mutate(
      { id: propertyId, data: editData },
      {
        onSuccess: () => {
          setIsEditing(false);
          refetch();
        },
      }
    );
  };

  const handleBuyFraction = () => {
    const idempotencyKey = `buy-${propertyId}-${uuidv4()}`;
    buyFraction.mutate(
      {
        unitId: propertyId,
        percentage: buyPercentage,
        idempotencyKey,
      },
      {
        onSuccess: () => {
          setShowBuyModal(false);
          refetch();
        },
      }
    );
  };

  if (propertyLoading || tokenLoading || ownershipLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!property) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground/60">
        <Building2 className="w-12 h-12 mb-4 opacity-30" />
        <p className="text-lg">العقار غير موجود</p>
        <button
          onClick={() => router.push('/realestate')}
          className="mt-4 text-primary hover:underline flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          العودة إلى العقارات
        </button>
      </div>
    );
  }

  const totalOwned = ownerships?.reduce((sum, o) => sum + o.ownership_percentage, 0) || 0;
  const remainingPercentage = 100 - totalOwned;

  return (
    <div className="p-6 space-y-6">
      {/* زر العودة */}
      <button
        onClick={() => router.push('/realestate')}
        className="flex items-center gap-2 text-sm text-muted-foreground/60 hover:text-foreground/80 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        العودة إلى العقارات
      </button>

      {/* الهيدر مع الصورة */}
      <div className="relative overflow-hidden rounded-3xl bg-card/20 backdrop-blur-2xl border border-white/10">
        <div className="relative w-full h-64 md:h-80">
          {property.cover_image_url ? (
            <Image
              src={property.cover_image_url}
              alt={property.title}
              fill
              className="object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/5 to-secondary/5">
              <Building2 className="w-20 h-20 text-muted-foreground/20" />
            </div>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/20 to-transparent" />
        </div>

        <div className="relative -mt-16 px-6 pb-6">
          <div className="flex flex-col md:flex-row items-start md:items-end gap-4">
            <div className="w-20 h-20 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 flex items-center justify-center text-3xl shadow-lg">
              <Building2 className="w-10 h-10 text-primary/60" />
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-2xl md:text-3xl font-bold text-foreground/90 truncate">
                  {property.title}
                </h1>
                <span
                  className={cn(
                    "text-xs px-3 py-1 rounded-full border font-medium",
                    statusColors[property.status as keyof typeof statusColors] || 'border-white/10 text-muted-foreground'
                  )}
                >
                  {property.status || 'متاح'}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-4 mt-1 text-sm text-muted-foreground/60">
                <span className="flex items-center gap-1">
                  <Building2 className="w-4 h-4" />
                  {typeLabels[property.property_type] || property.property_type}
                </span>
                {property.location && (
                  <span className="flex items-center gap-1">
                    <MapPin className="w-4 h-4" />
                    {property.location}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Ruler className="w-4 h-4" />
                  {property.area_sqm} م²
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3 self-end">
              {!isEditing && (
                <button
                  onClick={handleEdit}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 transition-colors text-sm"
                >
                  <Edit className="w-4 h-4" />
                  تعديل
                </button>
              )}
              <button
                onClick={() => setShowBuyModal(true)}
                disabled={remainingPercentage <= 0}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 text-sm disabled:opacity-50"
              >
                <ShoppingCart className="w-4 h-4" />
                شراء حصة
              </button>
            </div>
          </div>

          {/* وضع التحرير */}
          {isEditing && (
            <div className="mt-4 p-4 rounded-2xl bg-white/5 border border-white/10 space-y-4">
              <h4 className="text-sm font-medium text-foreground/80 flex items-center gap-2">
                <Edit className="w-4 h-4" />
                تعديل العقار
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground/50">العنوان</label>
                  <input
                    type="text"
                    value={editData?.title || ''}
                    onChange={(e) => setEditData({ ...editData, title: e.target.value })}
                    className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground/50">السعر (MR_USDT)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={editData?.sale_price_mrusdt || ''}
                    onChange={(e) => setEditData({ ...editData, sale_price_mrusdt: parseFloat(e.target.value) })}
                    className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="text-xs text-muted-foreground/50">الوصف</label>
                  <textarea
                    value={editData?.description || ''}
                    onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                    rows={2}
                    className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm resize-none"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleSaveEdit}
                  disabled={updateProperty.isPending}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
                >
                  {updateProperty.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  حفظ التغييرات
                </button>
                <button
                  onClick={() => setIsEditing(false)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors text-sm"
                >
                  <X className="w-4 h-4" />
                  إلغاء
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* المعلومات التفصيلية */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* الوصف */}
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <h3 className="text-sm font-medium text-foreground/80 mb-2">📝 الوصف</h3>
          <p className="text-sm text-foreground/70 leading-relaxed">
            {property.description || 'لا يوجد وصف متاح'}
          </p>
        </div>

        {/* التفاصيل */}
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <h3 className="text-sm font-medium text-foreground/80 mb-2">📊 التفاصيل</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground/60">المساحة</span>
              <span className="text-foreground/80">{property.area_sqm} م²</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground/60">سعر البيع</span>
              <span className="text-foreground/80 font-medium">
                {property.sale_price_mrusdt?.toFixed(2) || 'غير محدد'} MR_USDT
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground/60">الإيجار الشهري</span>
              <span className="text-foreground/80">
                {property.rent_per_month_mrusdt?.toFixed(2) || 'غير محدد'} MR_USDT
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground/60">المالك</span>
              <span className="text-foreground/80">#{property.owner_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground/60">تاريخ الإنشاء</span>
              <span className="text-foreground/80">
                {format(new Date(property.created_at), 'dd/MM/yyyy')}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* التجزئة والملكية */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* التجزئة */}
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <h3 className="text-sm font-medium text-foreground/80 mb-2 flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary" />
            تجزئة الأصول
          </h3>
          {tokenization ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground/60">إجمالي الأسهم</span>
                <span className="text-foreground/80">{tokenization.total_shares}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground/60">سعر السهم</span>
                <span className="text-foreground/80">{tokenization.share_price_mrusdt} MR_USDT</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground/60">الحد الأدنى للاستثمار</span>
                <span className="text-foreground/80">{tokenization.minimum_investment_shares} سهم</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground/60">الحالة</span>
                <span
                  className={cn(
                    "text-xs px-2 py-0.5 rounded-full border",
                    tokenization.is_fully_subscribed
                      ? "border-emerald-500/30 text-emerald-500"
                      : "border-blue-500/30 text-blue-500"
                  )}
                >
                  {tokenization.is_fully_subscribed ? 'مكتمل' : 'نشط'}
                </span>
              </div>
              {tokenization.smart_contract_address && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground/60">العقد الذكي</span>
                  <span className="text-foreground/80 font-mono text-xs truncate max-w-[150px]">
                    {tokenization.smart_contract_address}
                  </span>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-4 text-muted-foreground/50 text-sm">
              <Sparkles className="w-6 h-6 mx-auto mb-2 opacity-30" />
              هذا العقار غير مجزأ حالياً
            </div>
          )}
        </div>

        {/* الملكية */}
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <h3 className="text-sm font-medium text-foreground/80 mb-2 flex items-center gap-2">
            <Users className="w-4 h-4 text-primary" />
            الملكية الجزئية
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground/60">إجمالي المالكين</span>
              <span className="text-foreground/80">{ownerships?.length || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground/60">النسبة المباعة</span>
              <span className="text-foreground/80">{totalOwned.toFixed(2)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground/60">المتبقي</span>
              <span className={cn(
                "font-medium",
                remainingPercentage > 10 ? "text-emerald-500" : "text-amber-500"
              )}>
                {remainingPercentage.toFixed(2)}%
              </span>
            </div>
            {ownerships && ownerships.length > 0 && (
              <div className="mt-2 pt-2 border-t border-white/5">
                <p className="text-xs text-muted-foreground/50 mb-1">آخر المالكين</p>
                {ownerships.slice(0, 3).map((o) => (
                  <div key={o.id} className="flex justify-between text-xs text-foreground/70 py-0.5">
                    <span>المستخدم #{o.owner_user_id}</span>
                    <span>{o.ownership_percentage}%</span>
                  </div>
                ))}
                {ownerships.length > 3 && (
                  <p className="text-xs text-muted-foreground/40 mt-1">+{ownerships.length - 3} آخرين</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* مودال شراء حصة */}
      {showBuyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200 p-4">
          <div className="relative w-full max-w-md p-6 rounded-3xl bg-card/80 backdrop-blur-3xl border border-white/15 shadow-[0_20px_80px_-20px_rgba(0,0,0,0.6)] animate-in zoom-in-95 duration-200">
            <div className="absolute top-0 left-0 right-0 h-1 rounded-t-3xl bg-gradient-to-r from-primary to-secondary" />

            <button
              onClick={() => setShowBuyModal(false)}
              className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4 text-muted-foreground/60" />
            </button>

            <h3 className="text-lg font-bold text-foreground/90 flex items-center gap-2">
              <ShoppingCart className="w-5 h-5 text-primary" />
              شراء حصة في العقار
            </h3>

            <div className="mt-4 space-y-4">
              <div>
                <label className="text-sm text-muted-foreground/60">نسبة الملكية المطلوبة (%)</label>
                <div className="flex items-center gap-4 mt-1.5">
                  <input
                    type="range"
                    min="1"
                    max={Math.min(remainingPercentage, 50)}
                    value={buyPercentage}
                    onChange={(e) => setBuyPercentage(parseInt(e.target.value))}
                    className="flex-1 accent-primary"
                    step="1"
                  />
                  <span className="text-lg font-bold text-primary min-w-[50px] text-center">
                    {buyPercentage}%
                  </span>
                </div>
                <p className="text-xs text-muted-foreground/40 mt-1">
                  الحد الأقصى المتاح: {remainingPercentage.toFixed(2)}%
                </p>
              </div>

              <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground/60">السعر الإجمالي المقدر</span>
                  <span className="text-foreground/80 font-medium">
                    {((property.sale_price_mrusdt || 0) * buyPercentage / 100).toFixed(2)} MR_USDT
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground/60">نسبة الملكية</span>
                  <span className="text-foreground/80">{buyPercentage}%</span>
                </div>
              </div>

              <button
                onClick={handleBuyFraction}
                disabled={buyFraction.isPending}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
              >
                {buyFraction.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {buyFraction.isPending ? 'جاري التنفيذ...' : 'تأكيد الشراء'}
              </button>

              <p className="text-[10px] text-muted-foreground/30 text-center">
                🔒 سيتم استخدام مفتاح Idempotency لمنع التكرار
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}