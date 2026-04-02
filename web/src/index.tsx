/* @refresh reload */
import { render } from "solid-js/web";
import { Router, Route } from "@solidjs/router";
import { QueryClient, QueryClientProvider } from "@tanstack/solid-query";
import "./styles.css";
import App from "./App";

// Lazy load pages
import LoginPage from "~/routes/login";
import SetupPage from "~/routes/setup";
import SSLSetupPage from "~/routes/setup-ssl";
import DashboardPage from "~/routes/dashboard";
import SettingsPage from "~/routes/settings";
import TradersPage from "~/routes/traders";
import NewTraderPage from "~/routes/traders-new";
import TraderDetailPage from "~/routes/trader-detail";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
  },
});

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root element not found");
}

render(
  () => (
    <QueryClientProvider client={queryClient}>
      <Router root={App}>
        {/* Public routes */}
        <Route path="/" component={LoginPage} />
        <Route path="/setup" component={SetupPage} />
        <Route path="/setup/ssl" component={SSLSetupPage} />

        {/* Protected routes */}
        <Route path="/dashboard" component={DashboardPage} />
        <Route path="/settings" component={SettingsPage} />
        <Route path="/traders" component={TradersPage} />
        <Route path="/traders/new" component={NewTraderPage} />
        <Route path="/traders/:id" component={TraderDetailPage} />
      </Router>
    </QueryClientProvider>
  ),
  root
);
