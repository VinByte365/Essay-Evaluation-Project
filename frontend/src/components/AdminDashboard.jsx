import React, { useState } from "react";
import Navbar from "./Navbar";
import UserManagement from "./UserManagement";
import EssayModeration from "./EssayModeration";
import CommentsReview from "./CommentsReview";
import Analytics from "./Analytics";
import styles from "../styles/AdminDashboard.module.css";

export default function AdminDashboard({ user }) {
  const [activeSection, setActiveSection] = useState(null);

  if (activeSection === "users")
    return <UserManagement goBack={() => setActiveSection(null)} user={user} />;
  if (activeSection === "essays")
    return <EssayModeration goBack={() => setActiveSection(null)} user={user} />;
  if (activeSection === "comments")
    return <CommentsReview goBack={() => setActiveSection(null)} user={user} />;
  if (activeSection === "analytics")
    return <Analytics goBack={() => setActiveSection(null)} user={user} />;

  return (
    <>
      <Navbar user={user} />
      <div className={styles.container}>
        <h2>Admin Dashboard</h2>
        <div className={styles.grid}>
          <div className={styles.card} onClick={() => setActiveSection("users")}>
            <h3>👥 Manage Users</h3>
            <p>Ban, unban, and manage user accounts</p>
          </div>
          <div className={styles.card} onClick={() => setActiveSection("essays")}>
            <h3>📝 Moderate Essays</h3>
            <p>Review and remove inappropriate content</p>
          </div>
          <div className={styles.card} onClick={() => setActiveSection("comments")}>
            <h3>💬 Review Comments</h3>
            <p>Moderate user comments and replies</p>
          </div>
          <div className={styles.card} onClick={() => setActiveSection("analytics")}>
            <h3>📊 Analytics</h3>
            <p>View platform statistics and insights</p>
          </div>
        </div>
      </div>
    </>
  );
}
