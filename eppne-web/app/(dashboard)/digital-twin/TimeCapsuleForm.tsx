// app/(dashboard)/digital-twin/time-capsule/page.tsx
'use client';

import { useState } from 'react';
import { useDigitalTwinStore } from '@/store/digitalTwinStore';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import { Loader2, Clock, Users, Lock } from 'lucide-react';

export default function TimeCapsulePage() {
  const router = useRouter();
  const { createTimeCapsule, isLoading } = useDigitalTwinStore();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    encrypted_payload_hash: '',
    video_will_ipfs: '',
    heartbeat_interval_days: 90,
    encrypted_credentials: '{}',
    beneficiaries: [{ beneficiary_user_id: '', relationship_type: '', heir_wallet_address: '' }],
  });

  const addBeneficiary = () => {
    setFormData({
      ...formData,
      beneficiaries: [
        ...formData.beneficiaries,
        { beneficiary_user_id: '', relationship_type: '', heir_wallet_address: '' },
      ],
    });
  };

  const removeBeneficiary = (index: number) => {
    setFormData({
      ...formData,
      beneficiaries: formData.beneficiaries.filter((_, i) => i !== index),
    });
  };

  const handleBeneficiaryChange = (index: number, field: string, value: string) => {
    const newBeneficiaries = [...formData.beneficiaries];
    newBeneficiaries[index] = { ...newBeneficiaries[index], [field]: value };
    setFormData({ ...formData, beneficiaries: newBeneficiaries });
  };

  const handleSubmit = async () => {
    if (!formData.encrypted_payload_hash.trim()) {
      toast.error('يرجى إدخال تجزئة البيانات المشفرة');
      return;
    }

    if (formData.beneficiaries.some(b => !b.beneficiary_user_id || !b.heir_wallet_address)) {
      toast.error('يرجى تعبئة بيانات جميع المستفيدين');
      return;
    }

    setIsSubmitting(true);
    try {
      await createTimeCapsule(
        {
          encrypted_payload_hash: formData.encrypted_payload_hash,
          video_will_ipfs: formData.video_will_ipfs || null,
          heartbeat_interval_days: formData.heartbeat_interval_days,
          encrypted_credentials: JSON.parse(formData.encrypted_credentials || '{}'),
        },
        formData.beneficiaries.map(b => ({
          beneficiary_user_id: parseInt(b.beneficiary_user_id),
          relationship_type: b.relationship_type || null,
          access_share_percentage: 100,
          heir_wallet_address: b.heir_wallet_address,
        }))
      );
      router.push('/dashboard/digital-twin');
    } catch (error: any) {
      toast.error(error.message || 'فشل إنشاء كبسولة الزمن');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="container mx-auto py-8 max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-primary/10 rounded-full">
          <Clock className="h-8 w-8 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">إنشاء كبسولة الزمن</h1>
          <p className="text-muted-foreground text-sm">
            احفظ بياناتك المهمة لتُفتح في المستقبل بواسطة المستفيدين الذين تختارهم
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>بيانات الكبسولة</CardTitle>
          <CardDescription>جميع البيانات ستُشفر وتُخزن بشكل آمن</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* البيانات المشفرة */}
          <div className="space-y-2">
            <Label htmlFor="payload-hash">تجزئة البيانات المشفرة *</Label>
            <Input
              id="payload-hash"
              placeholder="أدخل تجزئة IPFS للبيانات المشفرة"
              value={formData.encrypted_payload_hash}
              onChange={(e) => setFormData({ ...formData, encrypted_payload_hash: e.target.value })}
            />
            <p className="text-xs text-muted-foreground">
              يمكنك تشفير البيانات باستخدام أدوات التشفير ثم رفعها على IPFS
            </p>
          </div>

          {/* فيديو الوصية */}
          <div className="space-y-2">
            <Label htmlFor="video-will">فيديو الوصية (اختياري)</Label>
            <Input
              id="video-will"
              placeholder="رابط IPFS لفيديو الوصية"
              value={formData.video_will_ipfs}
              onChange={(e) => setFormData({ ...formData, video_will_ipfs: e.target.value })}
            />
          </div>

          {/* فترة النبض */}
          <div className="space-y-2">
            <Label htmlFor="heartbeat">فترة نبضة القلب (بالأيام)</Label>
            <Input
              id="heartbeat"
              type="number"
              min="1"
              max="365"
              value={formData.heartbeat_interval_days}
              onChange={(e) => setFormData({ ...formData, heartbeat_interval_days: parseInt(e.target.value) || 90 })}
            />
            <p className="text-xs text-muted-foreground">
              إذا توقفت نبضات القلب، سيتم اعتبار الكبسولة جاهزة للفتح
            </p>
          </div>

          {/* المستفيدين */}
          <div className="space-y-4 border-t pt-4">
            <div className="flex justify-between items-center">
              <Label className="text-base font-medium">المستفيدين</Label>
              <Button variant="outline" size="sm" onClick={addBeneficiary}>
                <Users className="mr-2 h-4 w-4" />
                إضافة مستفيد
              </Button>
            </div>

            {formData.beneficiaries.map((beneficiary, index) => (
              <div key={index} className="border rounded-lg p-4 space-y-3 relative">
                {formData.beneficiaries.length > 1 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute top-2 right-2 text-red-500 hover:text-red-700"
                    onClick={() => removeBeneficiary(index)}
                  >
                    ✕
                  </Button>
                )}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor={`beneficiary-id-${index}`}>معرف المستخدم *</Label>
                    <Input
                      id={`beneficiary-id-${index}`}
                      type="number"
                      placeholder="معرف المستخدم"
                      value={beneficiary.beneficiary_user_id}
                      onChange={(e) => handleBeneficiaryChange(index, 'beneficiary_user_id', e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor={`beneficiary-relation-${index}`}>نوع العلاقة</Label>
                    <Input
                      id={`beneficiary-relation-${index}`}
                      placeholder="مثل: زوج، ابن، صديق"
                      value={beneficiary.relationship_type}
                      onChange={(e) => handleBeneficiaryChange(index, 'relationship_type', e.target.value)}
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label htmlFor={`beneficiary-wallet-${index}`}>عنوان المحفظة الوريثة *</Label>
                  <Input
                    id={`beneficiary-wallet-${index}`}
                    placeholder="0x..."
                    value={beneficiary.heir_wallet_address}
                    onChange={(e) => handleBeneficiaryChange(index, 'heir_wallet_address', e.target.value)}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* بيانات إضافية */}
          <div className="space-y-2 border-t pt-4">
            <Label htmlFor="credentials">بيانات الاعتماد المشفرة (JSON)</Label>
            <Textarea
              id="credentials"
              rows={3}
              placeholder='{"accounts": {"email": "..."}, "notes": "..."}'
              value={formData.encrypted_credentials}
              onChange={(e) => setFormData({ ...formData, encrypted_credentials: e.target.value })}
            />
          </div>
        </CardContent>
        <CardFooter className="flex justify-end gap-2 border-t pt-4">
          <Button variant="outline" onClick={() => router.back()}>إلغاء</Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Lock className="mr-2 h-4 w-4" />}
            إنشاء الكبسولة
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}