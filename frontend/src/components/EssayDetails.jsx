import React, { useState } from "react";
import Navbar from "./Navbar";
import styles from "../styles/EssayDetails.module.css";

export default function EssayDetails({ essay, user, onBack, onDelete }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [likes, setLikes] = useState(essay.likes);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");

  const isAuthor = user.id === essay.authorId;

  function handleDelete() {
    if (isAuthor) {
      if (window.confirm("Delete this essay?")) {
        onDelete(essay.id);
      }
    } else {
      alert("Permission denied");
    }
  }

  function handleEdit() {
    if (isAuthor) {
      const newCaption = prompt("Edit caption:", essay.caption);
      if (newCaption) essay.caption = newCaption;
    } else {
      alert("Permission denied");
    }
  }

  function handleLike() {
    setLikes(likes + 1);
  }

  function handleComment() {
    if (newComment.trim()) {
      setComments([...comments, { id: Date.now(), text: newComment, author: user.username }]);
      setNewComment("");
    }
  }

  return (
    <>
      <Navbar user={user} />
      <div className={styles.container}>
        <button onClick={onBack} className={styles.backBtn}>← Back to Feed</button>
        <div className={styles.card}>
          <h2>{essay.caption}</h2>
          <p className={styles.author}>by {essay.author}</p>
          <p className={styles.content}>{essay.content}</p>
          <div className={styles.actions}>
            <button onClick={handleLike} className={styles.likeBtn}>
              ❤️ {likes}
            </button>
            <button onClick={() => setMenuOpen(!menuOpen)} className={styles.menuBtn}>
              ⋮
            </button>
          </div>
          {menuOpen && (
            <div className={styles.menu}>
              <button onClick={handleEdit}>Edit Caption</button>
              <button onClick={handleDelete}>Delete Essay</button>
              <button onClick={() => setMenuOpen(false)}>Close</button>
            </div>
          )}
          <div className={styles.commentSection}>
            <h3>Comments</h3>
            {comments.map(c => (
              <div key={c.id} className={styles.comment}>
                <strong>{c.author}:</strong> {c.text}
              </div>
            ))}
            <input
              type="text"
              placeholder="Add a comment..."
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
            />
            <button onClick={handleComment}>Post Comment</button>
          </div>
        </div>
      </div>
    </>
  );
}
