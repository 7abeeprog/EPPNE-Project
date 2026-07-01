// components/academy/OrgTree.tsx
"use client";

import React, { useMemo } from "react";
import { useAcademyEntities } from "@/hooks/useAcademyEntities";
import { useAcademyUIStore } from "@/store/academy-ui-store";
import { Skeleton } from "@/components/ui/skeleton";
import { Folder, FolderOpen, FileText, ChevronDown, ChevronLeft, Network } from "lucide-react";

// ✅ دالة بناء الشجرة (تُستخدم داخل useMemo)
function buildTree(flatEntities: any[]): any[] {
  const map: Record<number, any> = {};
  const roots: any[] = [];

  flatEntities.forEach((entity) => {
    map[entity.id] = { ...entity, children: [] };
  });

  flatEntities.forEach((entity) => {
    if (entity.parent_id && map[entity.parent_id]) {
      map[entity.parent_id].children.push(map[entity.id]);
    } else {
      roots.push(map[entity.id]);
    }
  });

  return roots;
}

// ✅ مكون عقدة الشجرة مع React.memo
const TreeNode = React.memo(
  ({
    node,
    expandedNodes,
    toggleNode,
    depth = 0,
  }: {
    node: any;
    expandedNodes: Record<number, boolean>;
    toggleNode: (id: number) => void;
    depth?: number;
  }) => {
    const hasChildren = node.children && node.children.length > 0;
    const isExpanded = expandedNodes[node.id];

    return (
      <div
        className="relative"
        style={{ marginRight: depth > 0 ? `${depth * 8}px` : "0" }}
      >
        {depth > 0 && (
          <div className="absolute top-0 right-[-12px] w-px h-full bg-primary/20" />
        )}

        <div
          className={`flex items-center gap-3 cursor-pointer transition-all duration-300 group p-3 rounded-xl border ${
            isExpanded
              ? "bg-primary/5 border-primary/20"
              : "bg-background/40 hover:bg-primary/10 border-transparent hover:border-primary/30"
          }`}
          style={{ paddingRight: `${depth * 24 + 16}px` }}
          onClick={() => toggleNode(node.id)}
        >
          <div className="flex items-center justify-center text-primary/70 group-hover:text-primary transition-colors shrink-0">
            {hasChildren ? (
              isExpanded ? (
                <FolderOpen className="w-5 h-5 drop-shadow-sm" />
              ) : (
                <Folder className="w-5 h-5" />
              )
            ) : (
              <FileText className="w-5 h-5 text-emerald-500/70 group-hover:text-emerald-500" />
            )}
          </div>

          <span
            className={`font-bold tracking-wide flex-1 transition-colors ${
              isExpanded ? "text-primary" : "text-foreground group-hover:text-primary"
            }`}
          >
            {node.name}
          </span>

          {hasChildren && (
            <div className="text-muted-foreground/50 group-hover:text-primary transition-colors shrink-0">
              {isExpanded ? (
                <ChevronDown className="w-5 h-5" />
              ) : (
                <ChevronLeft className="w-5 h-5" />
              )}
            </div>
          )}
        </div>

        <div
          className={`overflow-hidden transition-all duration-500 ease-in-out origin-top ${
            isExpanded
              ? "max-h-[2000px] opacity-100 scale-y-100 mt-2"
              : "max-h-0 opacity-0 scale-y-0"
          }`}
        >
          {hasChildren &&
            isExpanded &&
            node.children.map((child: any) => (
              <TreeNode
                key={child.id}
                node={child}
                expandedNodes={expandedNodes}
                toggleNode={toggleNode}
                depth={depth + 1}
              />
            ))}
        </div>
      </div>
    );
  }
);

TreeNode.displayName = "TreeNode";

export const OrgTree = () => {
  // ✅ استخدام الهوك الجديد مع Pagination
  const { data: entitiesData, isLoading, isError } = useAcademyEntities(0, 100);
  const { expandedNodes, toggleNode } = useAcademyUIStore();

  // ✅ بناء الشجرة باستخدام useMemo
  const treeData = useMemo(() => {
    if (!entitiesData?.data) return [];
    return buildTree(entitiesData.data);
  }, [entitiesData]);

  if (isLoading) {
    return (
      <div className="p-6 md:p-8 bg-card/40 backdrop-blur-2xl rounded-[2rem] border border-white/10 shadow-inner">
        <Skeleton className="h-8 w-1/2 mb-8 bg-primary/10" />
        <div className="space-y-4 mr-2">
          <Skeleton className="h-10 w-3/4 bg-card/50 rounded-xl" />
          <Skeleton className="h-10 w-1/2 bg-card/50 rounded-xl mr-8" />
          <Skeleton className="h-10 w-2/3 bg-card/50 rounded-xl mr-8" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6 bg-destructive/10 backdrop-blur-md rounded-[2rem] border border-destructive/20 text-destructive font-bold text-center">
        فشل في جلب الهيكلة الأكاديمية. يرجى التحقق من الاتصال بالخادم السيادي.
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 bg-card/40 backdrop-blur-2xl rounded-[2.5rem] border border-primary/20 shadow-[0_0_40px_-15px_rgba(var(--primary-rgb),0.2)] relative overflow-hidden">
      {/* إضاءة خلفية نيون */}
      <div className="absolute top-0 right-0 w-48 h-48 bg-primary/10 blur-[100px] rounded-full pointer-events-none" />

      <h3 className="text-2xl mb-8 font-black text-foreground flex items-center justify-between border-b border-border/50 pb-6 relative z-10">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-primary/10 rounded-xl border border-primary/20 shadow-inner">
            <Network className="w-6 h-6 text-primary" />
          </div>
          الهيكل التنظيمي الأكاديمي
        </div>
        <div className="flex h-3 w-3 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
          <span className="relative inline-flex rounded-full h-3 w-3 bg-primary" />
        </div>
      </h3>

      <div className="space-y-2 relative z-10">
        {treeData.map((node: any) => (
          <TreeNode
            key={node.id}
            node={node}
            expandedNodes={expandedNodes}
            toggleNode={toggleNode}
            depth={0}
          />
        ))}
      </div>
    </div>
  );
};