import React from "react";
import Navbar from "./Navbar";
import styles from "../styles/AdminDashboard.module.css";

export default function CommentsReview({ goBack, user }) {
  return (
    <>
      <Navbar user={user} />
      <div className={styles.container}>
        <button onClick={goBack}>← Back to Dashboard</button>
        <h2>Comments Review</h2>
        <p>List of comments with delete options will appear here.</p>
      </div>
    </>
  );
}
