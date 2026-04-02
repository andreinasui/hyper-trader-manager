import { type Component, type JSX } from "solid-js";
import { Sidebar } from "./Sidebar";

interface AppShellProps {
  children: JSX.Element;
}

export const AppShell: Component<AppShellProps> = (props) => {
  return (
    <div class="min-h-screen bg-background">
      <Sidebar />
      <main class="lg:pl-64">
        <div class="p-6 lg:p-8">{props.children}</div>
      </main>
    </div>
  );
};
