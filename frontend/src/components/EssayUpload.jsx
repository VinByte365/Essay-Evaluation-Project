import React, { useState } from "react";
import Navbar from "./Navbar";
import styles from "../styles/EssayUpload.module.css";

export default function EssayUpload({ onCancel, onUpload, user }) {
  const [file, setFile] = useState(null);
  const [caption, setCaption] = useState("");
  const [visibility, setVisibility] = useState("public");
  const [score, setScore] = useState(null);

  function handleEvaluate() {
    setScore((Math.random() * 100).toFixed(2));
  }

  function handleSubmit() {
    const newEssay = {
      id: Date.now().toString(),
      author: user.username,
      authorId: user.id,
      caption,
      content: "Sample essay content from uploaded file...",
      likes: 0,
      comments: 0,
      visibility,
      score,
    };
    onUpload(newEssay);
  }

  return (
    <>
      <Navbar user={user} />
      <div className={styles.centeredOuter}>
        <div className={styles.card}>
          <h3>Upload Essay</h3>
          <input
            type="text"
            placeholder="Essay caption"
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            className={styles.input}
          />
          <input
            type="file"
            onChange={(e) => setFile(e.target.files[0])}
            className={styles.fileInput}
          />
          <button
            className={styles.button}
            onClick={handleEvaluate}
            disabled={!file}
          >
            Run NLP Evaluation
          </button>
          {score && <div className={styles.result}>Score: {score}</div>}
          <div className={styles.radioGroup}>
            <label className={styles.radioLabel}>
              <input
                type="radio"
                checked={visibility === "public"}
                onChange={() => setVisibility("public")}
              />
              Public
            </label>
            <label className={styles.radioLabel}>
              <input
                type="radio"
                checked={visibility === "friends"}
                onChange={() => setVisibility("friends")}
              />
              Friends
            </label>
          </div>
          <button
            className={styles.button}
            onClick={handleSubmit}
            disabled={!score || !caption}
          >
            Upload to Feed
          </button>
          <button className={styles.cancelBtn} onClick={onCancel}>
            Cancel
          </button>
        </div>
      </div>
    </>
  );
}
