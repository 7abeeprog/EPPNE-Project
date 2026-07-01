// store/cart-store.ts
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { CartItem, ProductVariant } from "@/types/commerce";

interface CartState {
  items: CartItem[];
  // ✅ دوال السلة
  addItem: (variant: ProductVariant, quantity: number) => void;
  removeItem: (variantId: number) => void;
  updateQuantity: (variantId: number, quantity: number) => void;
  clearCart: () => void;
  getTotalItems: () => number;
  getTotalPrice: () => number;
  getItemCount: (variantId: number) => number;
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],

      addItem: (variant: ProductVariant, quantity: number) => {
        const { items } = get();
        const existingIndex = items.findIndex((item) => item.variant_id === variant.id);

        if (existingIndex >= 0) {
          const newItems = [...items];
          newItems[existingIndex] = {
            ...newItems[existingIndex],
            quantity: newItems[existingIndex].quantity + quantity,
          };
          set({ items: newItems });
        } else {
          set({
            items: [
              ...items,
              {
                variant_id: variant.id,
                quantity,
                variant,
              },
            ],
          });
        }
      },

      removeItem: (variantId: number) => {
        const { items } = get();
        set({ items: items.filter((item) => item.variant_id !== variantId) });
      },

      updateQuantity: (variantId: number, quantity: number) => {
        if (quantity <= 0) {
          get().removeItem(variantId);
          return;
        }
        const { items } = get();
        set({
          items: items.map((item) =>
            item.variant_id === variantId ? { ...item, quantity } : item
          ),
        });
      },

      clearCart: () => {
        set({ items: [] });
      },

      getTotalItems: () => {
        const { items } = get();
        return items.reduce((acc, item) => acc + item.quantity, 0);
      },

      getTotalPrice: () => {
        const { items } = get();
        return items.reduce((acc, item) => {
          const price = item.variant?.discount_price || item.variant?.price_mrusdt || 0;
          return acc + price * item.quantity;
        }, 0);
      },

      getItemCount: (variantId: number) => {
        const { items } = get();
        const item = items.find((i) => i.variant_id === variantId);
        return item?.quantity || 0;
      },
    }),
    {
      name: "cart-storage",
      storage: createJSONStorage(() => localStorage),
      // ✅ partialize: استثناء الكائنات الضخمة (product, variant) من التخزين
      partialize: (state) => ({
        items: state.items.map((item) => ({
          variant_id: item.variant_id,
          quantity: item.quantity,
          // ✅ نحتفظ فقط بالمعرفات، ونستثني الكائنات الكاملة
        })),
      }),
      // ✅ عند استعادة البيانات، نقوم بإعادة بناء الكائنات من الـ API
      // سيتم ذلك في الـ useEffect الخاص بـ CartPage
    }
  )
);