import * as Dialog from "@radix-ui/react-dialog";
import { cva } from "class-variance-authority";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
export const cn = (...a) => twMerge(clsx(a));

const button = cva("inline-flex items-center gap-2 rounded-md text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed", {
  variants: {
    tone: { primary: "bg-pen text-white hover:opacity-90", plain: "border border-rule bg-sheet hover:border-pen", quiet: "hover:bg-penwash" },
    size: { md: "px-3.5 py-2", sm: "px-2.5 py-1 text-xs" },
  },
  defaultVariants: { tone: "plain", size: "md" },
});
export const Button = ({ tone, size, className, ...p }) => <button className={cn(button({ tone, size }), className)} {...p} />;

const STAMP = { approved: ["text-ok", "批准"], uncertain: ["text-hold", "待人工"], rejected: ["text-bad", "拒绝"], rule: ["text-bad", "存为规则"],
  none: ["text-ok", "未写入"], pass: ["text-ok", "通过"], fail: ["text-bad", "未通过"], refused: ["text-bad", "拒绝"], done: ["text-ok", "完成"],
  superseded: ["text-soft", "已取代"], retired: ["text-soft", "已撤回"] };
export function Stamp({ kind, label, className }) {
  const [c, t] = STAMP[kind] || ["text-soft", kind];
  return <span className={cn("stamp text-xs", c, className)}>{label || t}</span>;
}
export const Tag = ({ tone = "pen", children, className }) => {
  const m = { pen: "bg-penwash text-pen", ok: "bg-okwash text-ok", hold: "bg-holdwash text-hold", bad: "bg-badwash text-bad", soft: "bg-code text-soft" };
  return <span className={cn("rounded px-1.5 py-0.5 text-xs font-medium font-mono", m[tone], className)}>{children}</span>;
};
export const Panel = ({ title, aside, children, className }) => (
  <section className={cn("rounded-lg border border-rule bg-sheet", className)}>
    {title && <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule px-4 py-2.5"><h3 className="m-0 text-[15px] font-bold">{title}</h3>{aside}</header>}
    <div className="min-w-0 p-4">{children}</div>
  </section>
);
export const Code = ({ children, className }) => <pre className={cn("out m-0 rounded-md bg-code px-3 py-2 font-mono text-[12.5px] leading-relaxed", className)}>{children}</pre>;
export const Source = ({ children }) => <p className="m-0 text-xs text-soft">来源：{children}</p>;

export function Drawer({ open, onOpenChange, title, children }) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30" />
        <Dialog.Content className="fixed bottom-0 right-0 top-0 flex w-[min(640px,100vw)] flex-col border-l border-rule bg-sheet shadow-xl" style={{ paddingTop: "env(safe-area-inset-top,0px)" }}>
          <div className="flex items-start justify-between gap-3 border-b border-rule px-5 py-3">
            <Dialog.Title className="m-0 text-lg font-bold">{title}</Dialog.Title>
            <Dialog.Close asChild><Button size="sm" aria-label="关闭">关闭</Button></Dialog.Close>
          </div>
          <Dialog.Description className="sr-only">证据详情</Dialog.Description>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
