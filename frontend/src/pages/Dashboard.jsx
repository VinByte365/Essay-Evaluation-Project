import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import AdminDashboard from "../components/AdminDashboard";
import UserFeed from "../components/UserFeed";

export default function Dashboard() {
  const location = useLocation();
  const user = location.state?.user;

  if (!user) {
    return <Navigate to="/" />;
  }

  return user.role === "admin" ? (
    <AdminDashboard user={user} />
  ) : (
    <UserFeed user={user} />
  );
}
