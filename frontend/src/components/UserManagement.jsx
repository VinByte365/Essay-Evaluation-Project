import React from "react";
import Navbar from "./Navbar";
import styles from "../styles/AdminDashboard.module.css";

export default function UserManagement({ goBack, user }) {
  const users = [
    { id: 1, username: "user1", status: "active" },
    { id: 2, username: "user2", status: "banned" },
  ];

  return (
    <>
      <Navbar user={user} />
      <div className={styles.container}>
        <button onClick={goBack}>← Back to Dashboard</button>
        <h2>User Management</h2>
        <table style={{ width: "100%", marginTop: "1rem", background: "white", borderRadius: "8px", padding: "1rem" }}>
          <thead>
            <tr>
              <th>Username</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{u.status}</td>
                <td>
                  <button onClick={() => alert(`Toggle ban for ${u.username}`)}>
                    {u.status === "active" ? "Ban" : "Unban"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
