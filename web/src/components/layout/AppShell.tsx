import { type Component, type JSX, createSignal } from "solid-js";
import { Sidebar } from "./Sidebar";
import { UpdateBanner } from "~/components/UpdateBanner";

interface AppShellProps {
  children: JSX.Element;
}

export const AppShell: Component<AppShellProps> = (props) => {
  const [expanded, setExpanded] = createSignal(true);

  return (
    <div class="min-h-screen bg-surface-base">
      <Sidebar expanded={expanded()} onToggle={() => setExpanded((v) => !v)} />
      <main
        class="transition-all duration-200 min-h-screen flex flex-col"
        style={{ "margin-left": expanded() ? "220px" : "64px" }}
      >
        <UpdateBanner />
        {props.children}
      </main>
    </div>
  );
};
