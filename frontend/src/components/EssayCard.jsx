import React from "react";
import styles from "../styles/EssayCard.module.css";

export default function EssayCard({ essay, onClick }) {
  return (
    <div className={styles.card} onClick={onClick}>
      <h3>{essay.caption}</h3>
      <p className={styles.author}>by {essay.author}</p>
      <p className={styles.preview}>{essay.content.substring(0, 150)}...</p>
      <div className={styles.stats}>
        <span>❤️ {essay.likes}</span>
        <span>💬 {essay.comments}</span>
      </div>
    </div>
  );
}
