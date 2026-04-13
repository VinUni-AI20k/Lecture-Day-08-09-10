"use client";

import * as React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Separator } from "@/components/ui/separator";
import { getRagApiBase } from "@/lib/rag-client";

export interface Settings {
  mode: "dense" | "sparse" | "hybrid";
  useRerank: boolean;
  topKSearch: number;
  topKSelect: number;
}

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  settings: Settings;
  onChange: (s: Settings) => void;
}

export function SettingsDrawer({ open, onOpenChange, settings, onChange }: Props) {
  const api = getRagApiBase();

  function patch(partial: Partial<Settings>) {
    onChange({ ...settings, ...partial });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <DialogTitle>Cài đặt Retrieval</DialogTitle>
          <DialogDescription>
            Điều chỉnh tham số RAG pipeline. Thay đổi có hiệu lực ngay lần
            gửi tiếp theo.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          {/* Retrieval mode */}
          <div className="space-y-2">
            <Label htmlFor="mode-select">Chế độ retrieval</Label>
            <Select
              value={settings.mode}
              onValueChange={(v) =>
                patch({ mode: v as Settings["mode"] })
              }
            >
              <SelectTrigger id="mode-select" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="dense">Dense (vector)</SelectItem>
                <SelectItem value="sparse">Sparse (BM25)</SelectItem>
                <SelectItem value="hybrid">Hybrid (Dense + Sparse)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Separator />

          {/* top_k_search */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>top_k_search</Label>
              <span className="text-sm font-mono text-muted-foreground">
                {settings.topKSearch}
              </span>
            </div>
            <Slider
              min={1}
              max={20}
              step={1}
              value={[settings.topKSearch]}
              onValueChange={([v]) => patch({ topKSearch: v })}
            />
            <p className="text-xs text-muted-foreground">
              Số chunk lấy từ vector store trước khi lọc.
            </p>
          </div>

          {/* top_k_select */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>top_k_select</Label>
              <span className="text-sm font-mono text-muted-foreground">
                {settings.topKSelect}
              </span>
            </div>
            <Slider
              min={1}
              max={settings.topKSearch}
              step={1}
              value={[settings.topKSelect]}
              onValueChange={([v]) => patch({ topKSelect: v })}
            />
            <p className="text-xs text-muted-foreground">
              Số chunk đưa vào prompt sau khi rerank / lọc.
            </p>
          </div>

          <Separator />

          {/* Rerank */}
          <div className="flex items-center justify-between gap-4">
            <div>
              <Label htmlFor="rerank-switch">Cross-encoder Rerank</Label>
              <p className="text-xs text-muted-foreground mt-0.5">
                Sắp xếp lại chunk bằng model cross-encoder (chậm hơn, chính
                xác hơn).
              </p>
            </div>
            <Switch
              id="rerank-switch"
              checked={settings.useRerank}
              onCheckedChange={(v) => patch({ useRerank: v })}
            />
          </div>

          <Separator />

          {/* API info */}
          <div className="rounded-lg bg-muted px-3 py-2.5 space-y-1">
            <p className="text-xs font-medium text-muted-foreground">
              FastAPI endpoint
            </p>
            <code className="text-xs break-all text-foreground">{api}/api/rag</code>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
