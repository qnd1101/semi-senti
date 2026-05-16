"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { StockTable } from "@/components/admin/stock-table";
import { SystemMonitor } from "@/components/admin/system-monitor";
import { ManualRefresh } from "@/components/admin/manual-refresh";

const MESSAGES = {
  title: "관리자 콘솔",
  subtitle: "종목 관리 · 시스템 모니터링 · 엔진 트리거",
  stockTab: "종목 관리",
  systemTab: "시스템 모니터",
  refreshTab: "수동 갱신",
  back: "대시보드로",
} as const;

export default function AdminPage() {
  return (
    <div className="min-h-screen bg-background p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            {MESSAGES.title}
          </h1>
          <p className="text-sm text-muted-foreground">{MESSAGES.subtitle}</p>
        </div>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/" className="gap-1">
            <ArrowLeft className="h-4 w-4" />
            {MESSAGES.back}
          </Link>
        </Button>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="stocks" className="w-full">
        <TabsList>
          <TabsTrigger value="stocks">{MESSAGES.stockTab}</TabsTrigger>
          <TabsTrigger value="system">{MESSAGES.systemTab}</TabsTrigger>
          <TabsTrigger value="refresh">{MESSAGES.refreshTab}</TabsTrigger>
        </TabsList>
        <TabsContent value="stocks" className="mt-4">
          <StockTable />
        </TabsContent>
        <TabsContent value="system" className="mt-4">
          <SystemMonitor />
        </TabsContent>
        <TabsContent value="refresh" className="mt-4">
          <ManualRefresh />
        </TabsContent>
      </Tabs>
    </div>
  );
}
