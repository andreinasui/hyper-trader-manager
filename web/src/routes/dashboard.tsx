import { Navigate } from "@solidjs/router";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import type { Component } from "solid-js";

const DashboardPage: Component = () => (
  <ProtectedRoute>
    <Navigate href="/traders" />
  </ProtectedRoute>
);

export default DashboardPage;
