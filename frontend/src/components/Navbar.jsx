import React from "react";
import { useNavigate } from "react-router-dom";
import styles from "../styles/Navbar.module.css";

export default function Navbar({ user }) {
  const navigate = useNavigate();

  function handleLogout() {
    navigate("/");
  }

  return (
    <nav className={styles.navbar}>
      <div className={styles.brand}>EssayHub</div>
      <div className={styles.right}>
        <span className={styles.username}>{user.username}</span>
        <button onClick={handleLogout} className={styles.logoutBtn}>
          Logout
        </button>
      </div>
    </nav>
  );
}
