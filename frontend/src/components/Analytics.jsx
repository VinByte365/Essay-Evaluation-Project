import React from "react";
import Navbar from "./Navbar";
import styles from "../styles/AdminDashboard.module.css";

export default function Analytics({ goBack, user }) {
  return (
    <>
      <Navbar user={user} />
      <div className={styles.container}>
        <button onClick={goBack}>← Back to Dashboard</button>
        <h2>Analytics Summary</h2>
        <p>Platform statistics and insights will be displayed here.</p>
      </div>
    </>
  );
}
