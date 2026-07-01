// app/(public)/public/[slug]/page.tsx
import { getPublicEntityPage } from '@/services/sovereign-entities';
import { getEntityCourses } from '@/services/academy';
import { getEntityProducts } from '@/services/commerce';
import { getEntityProjects } from '@/services/projects';
import { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import { cn } from '@/lib/utils';

// ISR: إعادة التصيير كل 5 دقائق
export const revalidate = 300;

// ========== جلب البيانات ==========
async function getPageData(slug: string) {
  const entityData = await getPublicEntityPage(slug);
  
  // جلب البيانات من القطاعات الأخرى بالتوازي
  const [courses, products, projects] = await Promise.all([
    getEntityCourses(entityData.entity.id).then(res => res.data || []),
    getEntityProducts(entityData.entity.id).then(res => res.data || []),
    getEntityProjects(entityData.entity.id).then(res => res.data || []),
  ]);

  return { ...entityData, courses, products, projects };
}

// ========== Metadata ==========
export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const data = await getPublicEntityPage(params.slug);
  return {
    title: data.page?.meta_title || data.entity.name,
    description: data.page?.meta_description || `الصفحة الرسمية لـ ${data.entity.name} على منصة EPPNE`,
    openGraph: {
      title: data.entity.name,
      description: data.page?.meta_description || `تعرف على ${data.entity.name} وخدماته`,
      images: data.entity.logo_url ? [{ url: data.entity.logo_url }] : [],
    },
  };
}

// ========== المكون الرئيسي ==========
export default async function PublicEntityPage({ params }: { params: { slug: string } }) {
  const { entity, page, courses, products, projects } = await getPageData(params.slug);

  const primary = entity.primary_color || '#8CC63F';
  const secondary = entity.secondary_color || '#06b6d4';

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background/95 to-background/90">
      {/* الهيدر – مع تدرج لوني مستوحى من الكيان */}
      <div 
        className="relative overflow-hidden"
        style={{
          background: `linear-gradient(135deg, ${primary}20 0%, ${secondary}10 100%)`,
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="flex flex-col md:flex-row items-center gap-8">
            {/* الشعار */}
            {entity.logo_url ? (
              <Image
                src={entity.logo_url}
                alt={entity.name}
                width={120}
                height={120}
                className="rounded-2xl border-2 border-white/10 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)]"
                style={{ '--primary-rgb': primary } as React.CSSProperties}
              />
            ) : (
              <div className="w-28 h-28 rounded-2xl bg-white/5 border-2 border-white/10 flex items-center justify-center text-4xl">
                🏛️
              </div>
            )}
            
            <div className="text-center md:text-right">
              <h1 className="text-3xl md:text-4xl font-bold text-foreground/90">
                {entity.name}
              </h1>
              <p className="text-foreground/60 mt-1">
                {entity.legal_name || entity.entity_type.replace(/_/g, ' ')}
              </p>
              {page.meta_description && (
                <p className="text-foreground/50 mt-2 max-w-xl">
                  {page.meta_description}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* البلوكات */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* الأكاديمية */}
        {courses.length > 0 && (
          <section className="p-6 rounded-2xl bg-card/30 backdrop-blur-xl border border-white/10">
            <h2 className="text-lg font-bold text-foreground/80 mb-4 flex items-center gap-2">
              📚 كورسات {entity.name}
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {courses.slice(0, 6).map((course: any) => (
                <Link
                  key={course.id}
                  href={`/academy/courses/${course.slug}?entity=${entity.id}`}
                  className="p-4 rounded-xl bg-white/5 hover:bg-white/10 transition-colors border border-white/5"
                >
                  <h4 className="font-medium text-foreground/80">{course.title}</h4>
                  <p className="text-xs text-muted-foreground/60 mt-1">{course.description?.slice(0, 80)}</p>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* المنتجات والخدمات */}
        {products.length > 0 && (
          <section className="p-6 rounded-2xl bg-card/30 backdrop-blur-xl border border-white/10">
            <h2 className="text-lg font-bold text-foreground/80 mb-4 flex items-center gap-2">
              🛍️ منتجات وخدمات
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {products.slice(0, 6).map((product: any) => (
                <div key={product.id} className="p-4 rounded-xl bg-white/5 border border-white/5">
                  <h4 className="font-medium text-foreground/80">{product.name}</h4>
                  <p className="text-xs text-muted-foreground/60 mt-1">{product.description?.slice(0, 60)}</p>
                  <p className="text-sm font-bold text-primary mt-2">
                    {product.price} {product.currency || 'MR_USDT'}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* المشاريع */}
        {projects.length > 0 && (
          <section className="p-6 rounded-2xl bg-card/30 backdrop-blur-xl border border-white/10">
            <h2 className="text-lg font-bold text-foreground/80 mb-4 flex items-center gap-2">
              🏗️ المشاريع النشطة
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {projects.slice(0, 4).map((project: any) => (
                <div key={project.id} className="p-4 rounded-xl bg-white/5 border border-white/5">
                  <h4 className="font-medium text-foreground/80">{project.title}</h4>
                  <p className="text-xs text-muted-foreground/60 mt-1">{project.status}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* شارة SaaS – مستوى الاشتراك */}
        <div className="flex justify-center pt-4">
          <div 
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-white/10 bg-card/30 backdrop-blur-xl"
          >
            <span className="text-sm text-foreground/60">
              عضو موثق في 
              <span className="font-bold text-foreground/80 mx-1">EPPNE</span>
              <span className="text-xs text-muted-foreground/50"> • مستوى {entity.entity_type}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}