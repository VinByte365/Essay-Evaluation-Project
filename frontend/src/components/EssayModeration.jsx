import React from "react";
import Navbar from "./Navbar";
import styles from "../styles/AdminDashboard.module.css";

export default function EssayModeration({ goBack, user }) {
  return (
    <>
      <Navbar user={user} />
      <div className={styles.container}>
        <button onClick={goBack}>← Back to Dashboard</button>
        <h2>Essay Moderation</h2>
        <p>List of essays with remove options will appear here.</p>
      </div>
    </>
  );
}
