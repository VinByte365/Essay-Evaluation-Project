import React, { useState } from "react";
import Navbar from "./Navbar";
import EssayUpload from "./EssayUpload";
import EssayDetails from "./EssayDetails";
import EssayCard from "./EssayCard";
import styles from "../styles/UserFeed.module.css";

const mockEssays = [
  { id: "e1", author: "user1", authorId: "2", caption: "My First Essay", content: "Lorem ipsum dolor sit amet...", likes: 5, comments: 2 },
  { id: "e2", author: "admin", authorId: "1", caption: "Admin Essay", content: "Another sample essay content...", likes: 10, comments: 4 },
];

export default function UserFeed({ user }) {
  const [uploading, setUploading] = useState(false);
  const [selectedEssay, setSelectedEssay] = useState(null);
  const [essays, setEssays] = useState(mockEssays);

  if (uploading)
    return (
      <EssayUpload
        onCancel={() => setUploading(false)}
        onUpload={(essay) => {
          setEssays([essay, ...essays]);
          setUploading(false);
        }}
        user={user}
      />
    );

  if (selectedEssay)
    return (
      <EssayDetails
        essay={selectedEssay}
        user={user}
        onBack={() => setSelectedEssay(null)}
        onDelete={(id) => {
          setEssays(essays.filter(e => e.id !== id));
          setSelectedEssay(null);
        }}
      />
    );

  return (
    <>
      <Navbar user={user} />
      <div className={styles.container}>
        <div className={styles.header}>
          <h2>Feed</h2>
          <button onClick={() => setUploading(true)} className={styles.uploadBtn}>
            + Upload Essay
          </button>
        </div>
        <div className={styles.feed}>
          {essays.map(essay => (
            <EssayCard
              key={essay.id}
              essay={essay}
              onClick={() => setSelectedEssay(essay)}
            />
          ))}
        </div>
      </div>
    </>
  );
}
